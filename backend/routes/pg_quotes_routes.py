"""
PostgreSQL Quotation Comparison Routes
Handles supplier offers comparison per request
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
import uuid
import json

from database import (
    get_postgres_session, QuotationComparison,
    MaterialRequest, MaterialRequestItem, User, AuditLog
)

from routes.pg_auth_routes import get_current_user_pg, UserRole

pg_quotes_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Quotations"])


class QuoteItem(BaseModel):
    item_index: int
    unit_price: float


class QuoteOffer(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: str
    items: List[QuoteItem]
    notes: Optional[str] = None


class QuoteCreate(BaseModel):
    request_id: str
    offers: List[QuoteOffer]
    notes: Optional[str] = None


class QuoteUpdate(BaseModel):
    offers: List[QuoteOffer]
    notes: Optional[str] = None


class QuoteSelect(BaseModel):
    offer_index: int


async def log_audit_pg(session, entity_type, entity_id, action, user, description, changes=None):
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=json.dumps(changes) if changes else None,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role,
        description=description
    )
    session.add(audit_log)


async def get_request_with_items(session: AsyncSession, request_id: str):
    req_result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == request_id)
    )
    request = req_result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")

    items_result = await session.execute(
        select(MaterialRequestItem)
        .where(MaterialRequestItem.request_id == request_id)
        .order_by(MaterialRequestItem.item_index)
    )
    request_items = items_result.scalars().all()
    return request, request_items


def normalize_offers(offers: List[QuoteOffer], request_items: List[MaterialRequestItem]):
    if not offers:
        raise HTTPException(status_code=400, detail="يجب إدخال عرض واحد على الأقل")

    expected_count = len(request_items)
    offers_payload = []

    for offer in offers:
        if not offer.supplier_name.strip():
            raise HTTPException(status_code=400, detail="اسم المورد مطلوب لكل عرض")

        if len(offer.items) != expected_count:
            raise HTTPException(status_code=400, detail="عدد الأصناف في العرض غير مطابق للطلب")

        offer_items_map = {item.item_index: item for item in offer.items}
        normalized_items = []
        total_amount = 0

        for idx, req_item in enumerate(request_items):
            if idx not in offer_items_map:
                raise HTTPException(status_code=400, detail=f"الصنف رقم {idx + 1} مفقود من العرض")

            offer_item = offer_items_map[idx]
            unit_price = float(offer_item.unit_price or 0)
            if unit_price < 0:
                raise HTTPException(status_code=400, detail="سعر الوحدة لا يمكن أن يكون سالباً")

            item_total = unit_price * req_item.quantity
            total_amount += item_total

            normalized_items.append({
                "item_index": idx,
                "name": req_item.name,
                "quantity": req_item.quantity,
                "unit": req_item.unit,
                "unit_price": unit_price,
                "total_price": item_total
            })

        offers_payload.append({
            "supplier_id": offer.supplier_id,
            "supplier_name": offer.supplier_name.strip(),
            "items": normalized_items,
            "notes": offer.notes,
            "total_amount": total_amount
        })

    return offers_payload


def serialize_quote(quote: QuotationComparison):
    offers = json.loads(quote.offers or "[]")
    selected_offer = None
    if quote.selected_offer_index is not None and quote.selected_offer_index < len(offers):
        selected_offer = offers[quote.selected_offer_index]

    return {
        "id": quote.id,
        "request_id": quote.request_id,
        "request_number": quote.request_number,
        "project_id": quote.project_id,
        "project_name": quote.project_name,
        "status": quote.status,
        "offers": offers,
        "selected_offer_index": quote.selected_offer_index,
        "selected_supplier_id": quote.selected_supplier_id,
        "selected_supplier_name": quote.selected_supplier_name,
        "selected_total_amount": quote.selected_total_amount,
        "converted_order_id": quote.converted_order_id,
        "notes": quote.notes,
        "created_by_name": quote.created_by_name,
        "created_at": quote.created_at.isoformat() if quote.created_at else None,
        "updated_at": quote.updated_at.isoformat() if quote.updated_at else None,
        "selected_offer": selected_offer
    }


@pg_quotes_router.get("/quotes")
async def list_quotes(
    request_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """List quotation comparisons - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    query = select(QuotationComparison)
    if request_id:
        query = query.where(QuotationComparison.request_id == request_id)
    if status:
        query = query.where(QuotationComparison.status == status)

    query = query.order_by(desc(QuotationComparison.created_at))
    result = await session.execute(query)
    quotes = result.scalars().all()
    return [serialize_quote(q) for q in quotes]


@pg_quotes_router.get("/quotes/{quote_id}")
async def get_quote(
    quote_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single quotation comparison"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    result = await session.execute(
        select(QuotationComparison).where(QuotationComparison.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="المقارنة غير موجودة")

    return serialize_quote(quote)


@pg_quotes_router.post("/quotes")
async def create_quote(
    data: QuoteCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create or update quotation comparison - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    request, request_items = await get_request_with_items(session, data.request_id)
    if request.status not in ["approved_by_engineer", "partially_ordered"]:
        raise HTTPException(status_code=400, detail="الطلب غير جاهز لمقارنة العروض")

    offers_payload = normalize_offers(data.offers, request_items)

    existing_result = await session.execute(
        select(QuotationComparison).where(QuotationComparison.request_id == data.request_id)
    )
    existing = existing_result.scalar_one_or_none()

    now = datetime.utcnow()
    if existing:
        existing.offers = json.dumps(offers_payload, ensure_ascii=False)
        existing.notes = data.notes
        existing.status = "draft"
        existing.selected_offer_index = None
        existing.selected_supplier_id = None
        existing.selected_supplier_name = None
        existing.selected_total_amount = None
        existing.updated_at = now

        await log_audit_pg(
            session, "quotation", existing.id, "update", current_user,
            f"تحديث مقارنة عروض الأسعار للطلب: {request.request_number}"
        )
        await session.commit()
        return serialize_quote(existing)

    new_quote = QuotationComparison(
        id=str(uuid.uuid4()),
        request_id=request.id,
        request_number=request.request_number,
        project_id=request.project_id,
        project_name=request.project_name,
        status="draft",
        offers=json.dumps(offers_payload, ensure_ascii=False),
        notes=data.notes,
        created_by=current_user.id,
        created_by_name=current_user.name,
        created_at=now,
        updated_at=now
    )
    session.add(new_quote)

    await log_audit_pg(
        session, "quotation", new_quote.id, "create", current_user,
        f"إنشاء مقارنة عروض أسعار للطلب: {request.request_number}"
    )
    await session.commit()

    return serialize_quote(new_quote)


@pg_quotes_router.put("/quotes/{quote_id}")
async def update_quote(
    quote_id: str,
    data: QuoteUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update quotation comparison - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    result = await session.execute(
        select(QuotationComparison).where(QuotationComparison.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="المقارنة غير موجودة")

    request, request_items = await get_request_with_items(session, quote.request_id)
    offers_payload = normalize_offers(data.offers, request_items)

    quote.offers = json.dumps(offers_payload, ensure_ascii=False)
    quote.notes = data.notes
    quote.status = "draft"
    quote.selected_offer_index = None
    quote.selected_supplier_id = None
    quote.selected_supplier_name = None
    quote.selected_total_amount = None
    quote.updated_at = datetime.utcnow()

    await log_audit_pg(
        session, "quotation", quote.id, "update", current_user,
        f"تحديث مقارنة عروض الأسعار للطلب: {request.request_number}"
    )
    await session.commit()

    return serialize_quote(quote)


@pg_quotes_router.post("/quotes/{quote_id}/select")
async def select_quote_offer(
    quote_id: str,
    data: QuoteSelect,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Select winning offer for comparison"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    result = await session.execute(
        select(QuotationComparison).where(QuotationComparison.id == quote_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="المقارنة غير موجودة")

    offers = json.loads(quote.offers or "[]")
    if data.offer_index < 0 or data.offer_index >= len(offers):
        raise HTTPException(status_code=400, detail="العرض المحدد غير صالح")

    selected_offer = offers[data.offer_index]
    quote.selected_offer_index = data.offer_index
    quote.selected_supplier_id = selected_offer.get("supplier_id")
    quote.selected_supplier_name = selected_offer.get("supplier_name")
    quote.selected_total_amount = selected_offer.get("total_amount")
    quote.status = "selected"
    quote.updated_at = datetime.utcnow()

    await log_audit_pg(
        session, "quotation", quote.id, "select", current_user,
        f"اختيار العرض الفائز للطلب: {quote.request_number}"
    )
    await session.commit()

    return serialize_quote(quote)

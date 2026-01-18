"""
PostgreSQL Purchase Orders Routes
Migrated from MongoDB to PostgreSQL
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_, or_
import uuid
import json

from database import (
    get_postgres_session, PurchaseOrder, PurchaseOrderItem,
    MaterialRequest, MaterialRequestItem, User, Project, 
    Supplier, BudgetCategory, SystemSetting, AuditLog, PriceCatalogItem
)

# Create router
pg_orders_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Purchase Orders"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class PurchaseOrderItemPrice(BaseModel):
    index: int
    unit_price: float


class PurchaseOrderCreate(BaseModel):
    request_id: str
    supplier_id: Optional[str] = None
    supplier_name: str
    selected_items: List[int]  # Indices of items from original request
    item_prices: Optional[List[dict]] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    expected_delivery_date: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    item_prices: Optional[List[dict]] = None
    category_id: Optional[str] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    supplier_invoice_number: Optional[str] = None


# ==================== HELPER FUNCTIONS ====================

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


async def get_next_order_number(session: AsyncSession) -> tuple:
    """Get next sequential order number"""
    result = await session.execute(
        select(func.max(PurchaseOrder.order_seq))
    )
    max_seq = result.scalar() or 0
    next_seq = max_seq + 1
    
    # Format: PO-00000001
    order_number = f"PO-{next_seq:08d}"
    return order_number, next_seq


async def get_approval_limit(session: AsyncSession) -> float:
    """Get the approval limit from system settings"""
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "approval_limit")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        try:
            return float(setting.value)
        except ValueError:
            return 20000.0
    return 20000.0


async def get_order_items_map(session: AsyncSession, order_ids: List[str]):
    if not order_ids:
        return {}
    items_result = await session.execute(
        select(PurchaseOrderItem)
        .where(PurchaseOrderItem.order_id.in_(order_ids))
        .order_by(PurchaseOrderItem.order_id, PurchaseOrderItem.item_index)
    )
    items = items_result.scalars().all()
    items_map: dict[str, list[PurchaseOrderItem]] = {}
    for item in items:
        items_map.setdefault(item.order_id, []).append(item)
    return items_map


# ==================== PURCHASE ORDERS ROUTES ====================

@pg_orders_router.post("/purchase-orders")
async def create_purchase_order(
    order_data: PurchaseOrderCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a purchase order - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إصدار أوامر الشراء")
    
    if not order_data.supplier_name or not order_data.supplier_name.strip():
        raise HTTPException(status_code=400, detail="اسم المورد مطلوب")

    # Get material request
    req_result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == order_data.request_id)
    )
    request = req_result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if request.status not in ["approved_by_engineer", "partially_ordered"]:
        raise HTTPException(status_code=400, detail="الطلب غير جاهز لإصدار أمر شراء")
    
    # Get request items
    items_result = await session.execute(
        select(MaterialRequestItem)
        .where(MaterialRequestItem.request_id == order_data.request_id)
        .order_by(MaterialRequestItem.item_index)
    )
    request_items = items_result.scalars().all()
    
    # Validate selected items
    if not order_data.selected_items:
        raise HTTPException(status_code=400, detail="يجب اختيار صنف واحد على الأقل")

    if len(set(order_data.selected_items)) != len(order_data.selected_items):
        raise HTTPException(status_code=400, detail="لا يمكن اختيار نفس الصنف أكثر من مرة")
    
    for idx in order_data.selected_items:
        if idx < 0 or idx >= len(request_items):
            raise HTTPException(status_code=400, detail=f"فهرس الصنف {idx} غير صالح")
    
    # Get category name if provided
    category_name = None
    if order_data.category_id:
        cat_result = await session.execute(
            select(BudgetCategory).where(BudgetCategory.id == order_data.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            category_name = category.name
    
    # Create order
    order_id = str(uuid.uuid4())
    now = datetime.utcnow()
    order_number, order_seq = await get_next_order_number(session)
    
    # Calculate total amount and create items
    total_amount = 0
    order_items = []
    
    # Build price map and catalog item map from item_prices
    price_map = {}
    catalog_item_map = {}  # {index: {catalog_item_id, item_code}}
    if order_data.item_prices:
        for price_info in order_data.item_prices:
            idx = price_info.get("index", -1)
            if idx not in order_data.selected_items:
                raise HTTPException(status_code=400, detail=f"فهرس الصنف {idx} غير ضمن العناصر المختارة")
            unit_price = price_info.get("unit_price", 0)
            if unit_price is None or unit_price < 0:
                raise HTTPException(status_code=400, detail="سعر الوحدة يجب أن يكون رقمًا موجبًا")
            price_map[idx] = unit_price
            # Get catalog item info if provided
            catalog_item_id = price_info.get("catalog_item_id")
            if catalog_item_id:
                catalog_item_map[idx] = {"catalog_item_id": catalog_item_id}
    
    # Fetch catalog item codes for linked items
    if catalog_item_map:
        catalog_ids = [info["catalog_item_id"] for info in catalog_item_map.values() if info.get("catalog_item_id")]
        if catalog_ids:
            catalog_result = await session.execute(
                select(PriceCatalogItem).where(PriceCatalogItem.id.in_(catalog_ids))
            )
            catalog_items_db = {item.id: item for item in catalog_result.scalars().all()}
            # Update catalog_item_map with item_code
            for idx, info in catalog_item_map.items():
                catalog_id = info.get("catalog_item_id")
                if catalog_id and catalog_id in catalog_items_db:
                    info["item_code"] = catalog_items_db[catalog_id].item_code
    
    for idx in order_data.selected_items:
        req_item = request_items[idx]
        unit_price = price_map.get(idx, req_item.estimated_price or 0)
        item_total = unit_price * req_item.quantity
        total_amount += item_total
        
        # Get catalog info for this item
        catalog_info = catalog_item_map.get(idx, {})
        
        order_items.append({
            "name": req_item.name,
            "quantity": req_item.quantity,
            "unit": req_item.unit,
            "unit_price": unit_price,
            "total_price": item_total,
            "index": idx,
            "catalog_item_id": catalog_info.get("catalog_item_id"),
            "item_code": catalog_info.get("item_code")
        })
    
    # Check if needs GM approval
    approval_limit = await get_approval_limit(session)
    needs_gm_approval = total_amount > approval_limit
    initial_status = "pending_gm_approval" if needs_gm_approval else "pending_approval"
    
    new_order = PurchaseOrder(
        id=order_id,
        order_number=order_number,
        order_seq=order_seq,
        request_id=request.id,
        request_number=request.request_number,
        project_id=request.project_id,
        project_name=request.project_name,
        supplier_id=order_data.supplier_id,
        supplier_name=order_data.supplier_name,
        category_id=order_data.category_id,
        category_name=category_name,
        manager_id=current_user.id,
        manager_name=current_user.name,
        supervisor_name=request.supervisor_name,
        engineer_name=request.engineer_name,
        status=initial_status,
        needs_gm_approval=needs_gm_approval,
        total_amount=total_amount,
        notes=order_data.notes,
        terms_conditions=order_data.terms_conditions,
        expected_delivery_date=order_data.expected_delivery_date,
        created_at=now
    )
    session.add(new_order)
    
    # Create order items
    for idx, item_data in enumerate(order_items):
        order_item = PurchaseOrderItem(
            id=str(uuid.uuid4()),
            order_id=order_id,
            name=item_data["name"],
            quantity=item_data["quantity"],
            unit=item_data["unit"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"],
            item_index=idx,
            catalog_item_id=item_data.get("catalog_item_id"),
            item_code=item_data.get("item_code")
        )
        session.add(order_item)
    
    # Update request status
    all_items_ordered = len(order_data.selected_items) == len(request_items)
    if all_items_ordered:
        request.status = "purchase_order_issued"
    else:
        request.status = "partially_ordered"
    request.updated_at = now
    
    await log_audit_pg(
        session, "order", order_id, "create", current_user,
        f"إصدار أمر شراء: {order_number} بقيمة {total_amount}"
    )
    
    await session.commit()
    
    return {
        "id": order_id,
        "order_number": order_number,
        "order_seq": order_seq,
        "request_id": request.id,
        "request_number": request.request_number,
        "items": order_items,
        "project_name": request.project_name,
        "supplier_name": order_data.supplier_name,
        "category_name": category_name,
        "manager_name": current_user.name,
        "status": initial_status,
        "needs_gm_approval": needs_gm_approval,
        "total_amount": total_amount,
        "created_at": now.isoformat()
    }


@pg_orders_router.get("/purchase-orders")
async def get_purchase_orders(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    supplier_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get purchase orders based on user role"""
    allowed_roles = {
        UserRole.PROCUREMENT_MANAGER,
        UserRole.GENERAL_MANAGER,
        UserRole.PRINTER,
        UserRole.SYSTEM_ADMIN,
    }
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    query = select(PurchaseOrder)
    
    # Role-based filtering
    if current_user.role == UserRole.PRINTER:
        # Printer sees only approved orders
        query = query.where(PurchaseOrder.status.in_(["approved", "printed"]))
    elif current_user.role == UserRole.GENERAL_MANAGER:
        # GM sees orders needing approval + all orders
        pass
    elif current_user.role == UserRole.PROCUREMENT_MANAGER:
        # Manager sees all orders
        pass
    
    if status:
        query = query.where(PurchaseOrder.status == status)
    if project_id:
        query = query.where(PurchaseOrder.project_id == project_id)
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
    
    query = query.order_by(desc(PurchaseOrder.created_at))
    
    result = await session.execute(query)
    orders = result.scalars().all()

    order_ids = [order.id for order in orders]
    items_map = await get_order_items_map(session, order_ids)
    
    response = []
    for order in orders:
        items = items_map.get(order.id, [])
        
        response.append({
            "id": order.id,
            "order_number": order.order_number,
            "order_seq": order.order_seq,
            "request_id": order.request_id,
            "request_number": order.request_number,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "delivered_quantity": item.delivered_quantity,
                    "catalog_item_id": item.catalog_item_id,
                    "item_code": item.item_code
                }
                for item in items
            ],
            "project_id": order.project_id,
            "project_name": order.project_name,
            "supplier_id": order.supplier_id,
            "supplier_name": order.supplier_name,
            "category_id": order.category_id,
            "category_name": order.category_name,
            "manager_id": order.manager_id,
            "manager_name": order.manager_name,
            "supervisor_name": order.supervisor_name,
            "engineer_name": order.engineer_name,
            "status": order.status,
            "needs_gm_approval": order.needs_gm_approval,
            "approved_by_name": order.approved_by_name,
            "gm_approved_by_name": order.gm_approved_by_name,
            "total_amount": order.total_amount,
            "notes": order.notes,
            "supplier_invoice_number": order.supplier_invoice_number,
            "expected_delivery_date": order.expected_delivery_date,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "approved_at": order.approved_at.isoformat() if order.approved_at else None,
            "printed_at": order.printed_at.isoformat() if order.printed_at else None
        })
    
    return response


@pg_orders_router.get("/purchase-orders/{order_id}")
async def get_purchase_order(
    order_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single purchase order"""
    allowed_roles = {
        UserRole.PROCUREMENT_MANAGER,
        UserRole.GENERAL_MANAGER,
        UserRole.PRINTER,
        UserRole.SYSTEM_ADMIN,
    }
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")

    if current_user.role == UserRole.PRINTER and order.status not in ["approved", "printed"]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بالاطلاع على هذا الأمر")
    
    # Get items
    items_result = await session.execute(
        select(PurchaseOrderItem)
        .where(PurchaseOrderItem.order_id == order_id)
        .order_by(PurchaseOrderItem.item_index)
    )
    items = items_result.scalars().all()
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "order_seq": order.order_seq,
        "request_id": order.request_id,
        "request_number": order.request_number,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "delivered_quantity": item.delivered_quantity
            }
            for item in items
        ],
        "project_id": order.project_id,
        "project_name": order.project_name,
        "supplier_id": order.supplier_id,
        "supplier_name": order.supplier_name,
        "category_id": order.category_id,
        "category_name": order.category_name,
        "manager_id": order.manager_id,
        "manager_name": order.manager_name,
        "supervisor_name": order.supervisor_name,
        "engineer_name": order.engineer_name,
        "status": order.status,
        "needs_gm_approval": order.needs_gm_approval,
        "approved_by": order.approved_by,
        "approved_by_name": order.approved_by_name,
        "gm_approved_by": order.gm_approved_by,
        "gm_approved_by_name": order.gm_approved_by_name,
        "total_amount": order.total_amount,
        "notes": order.notes,
        "terms_conditions": order.terms_conditions,
        "expected_delivery_date": order.expected_delivery_date,
        "supplier_receipt_number": order.supplier_receipt_number,
        "supplier_invoice_number": order.supplier_invoice_number,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "approved_at": order.approved_at.isoformat() if order.approved_at else None,
        "gm_approved_at": order.gm_approved_at.isoformat() if order.gm_approved_at else None,
        "printed_at": order.printed_at.isoformat() if order.printed_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
    }


@pg_orders_router.put("/purchase-orders/{order_id}")
async def update_purchase_order(
    order_id: str,
    update_data: PurchaseOrderUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a purchase order - with approval limit check"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل أوامر الشراء")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    # Check if already approved by GM - can't modify
    if order.gm_approved_by:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل أمر شراء موافق عليه من المدير العام")
    
    changes = {}
    
    if update_data.supplier_name is not None:
        if not update_data.supplier_name.strip():
            raise HTTPException(status_code=400, detail="اسم المورد مطلوب")
        changes["supplier_name"] = {"old": order.supplier_name, "new": update_data.supplier_name}
        order.supplier_name = update_data.supplier_name
    
    if update_data.supplier_id is not None:
        order.supplier_id = update_data.supplier_id
    
    if update_data.notes is not None:
        order.notes = update_data.notes
    
    if update_data.terms_conditions is not None:
        order.terms_conditions = update_data.terms_conditions
    
    if update_data.expected_delivery_date is not None:
        order.expected_delivery_date = update_data.expected_delivery_date
    
    # Note: supplier_invoice_number can only be updated by Delivery Tracker
    # via the dedicated endpoint /purchase-orders/{order_id}/supplier-invoice
    
    if update_data.category_id is not None:
        order.category_id = update_data.category_id
        cat_result = await session.execute(
            select(BudgetCategory).where(BudgetCategory.id == update_data.category_id)
        )
        category = cat_result.scalar_one_or_none()
        if category:
            order.category_name = category.name
    
    # Update item prices if provided
    if update_data.item_prices:
        items_result = await session.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.order_id == order_id)
            .order_by(PurchaseOrderItem.item_index)
        )
        items = items_result.scalars().all()
        
        total_amount = 0
        for price_info in update_data.item_prices:
            item_name = price_info.get("name")
            unit_price = price_info.get("unit_price", 0)
            if unit_price is None or unit_price < 0:
                raise HTTPException(status_code=400, detail="سعر الوحدة يجب أن يكون رقمًا موجبًا")

            matched = False
            for item in items:
                if item.name == item_name:
                    item.unit_price = unit_price
                    item.total_price = unit_price * item.quantity
                    matched = True
                    break

            if not matched:
                raise HTTPException(status_code=400, detail=f"الصنف '{item_name}' غير موجود في أمر الشراء")
            
        # Recalculate total
        for item in items:
            total_amount += item.total_price
        
        old_total = order.total_amount
        order.total_amount = total_amount
        
        # Check if now needs GM approval
        approval_limit = await get_approval_limit(session)
        if total_amount > approval_limit and not order.needs_gm_approval:
            order.needs_gm_approval = True
            order.status = "pending_gm_approval"
            changes["needs_gm_approval"] = {"old": False, "new": True, "reason": f"المبلغ {total_amount} أكبر من حد الموافقة {approval_limit}"}
        if total_amount <= approval_limit and order.needs_gm_approval and order.status == "pending_gm_approval":
            order.needs_gm_approval = False
            order.status = "pending_approval"
            changes["needs_gm_approval"] = {"old": True, "new": False, "reason": f"المبلغ {total_amount} أقل من حد الموافقة {approval_limit}"}
    
    order.updated_at = datetime.utcnow()
    
    if changes:
        await log_audit_pg(
            session, "order", order_id, "update", current_user,
            f"تحديث أمر الشراء: {order.order_number}", changes
        )
    
    await session.commit()
    
    return {"message": "تم تحديث أمر الشراء بنجاح"}


@pg_orders_router.post("/purchase-orders/{order_id}/approve")
async def approve_purchase_order(
    order_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Approve a purchase order - manager or GM based on amount"""
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    now = datetime.utcnow()
    approval_limit = await get_approval_limit(session)
    
    # Check approval requirements
    if order.total_amount > approval_limit:
        # Needs GM approval
        if current_user.role != UserRole.GENERAL_MANAGER:
            raise HTTPException(
                status_code=403, 
                detail=f"أمر الشراء بقيمة {order.total_amount} يتجاوز حد الموافقة ({approval_limit}). يتطلب موافقة المدير العام"
            )
        
        if order.status != "pending_gm_approval":
            raise HTTPException(status_code=400, detail="أمر الشراء ليس في انتظار موافقة المدير العام")
        
        order.status = "approved"
        order.gm_approved_by = current_user.id
        order.gm_approved_by_name = current_user.name
        order.gm_approved_at = now
        
        await log_audit_pg(
            session, "order", order_id, "gm_approve", current_user,
            f"موافقة المدير العام على أمر الشراء: {order.order_number}"
        )
    else:
        # Manager can approve
        if current_user.role != UserRole.PROCUREMENT_MANAGER:
            raise HTTPException(status_code=403, detail="غير مصرح لك باعتماد هذا الأمر")
        
        if order.status != "pending_approval":
            raise HTTPException(status_code=400, detail="أمر الشراء ليس في انتظار الاعتماد")
        
        order.status = "approved"
        order.approved_by = current_user.id
        order.approved_by_name = current_user.name
        order.approved_at = now
        
        await log_audit_pg(
            session, "order", order_id, "approve", current_user,
            f"اعتماد أمر الشراء: {order.order_number}"
        )
    
    order.updated_at = now
    await session.commit()
    
    return {"message": "تم اعتماد أمر الشراء بنجاح", "status": "approved"}


class GMRejectData(BaseModel):
    reason: str


@pg_orders_router.post("/purchase-orders/{order_id}/gm-reject")
async def gm_reject_order(
    order_id: str,
    reject_data: GMRejectData,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Reject purchase order by General Manager"""
    if current_user.role != UserRole.GENERAL_MANAGER:
        raise HTTPException(status_code=403, detail="فقط المدير العام يمكنه رفض الأمر")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.status != "pending_gm_approval":
        raise HTTPException(status_code=400, detail="أمر الشراء ليس في انتظار موافقة المدير العام")
    
    order.status = "rejected_by_gm"
    order.rejection_reason = reject_data.reason
    order.updated_at = datetime.utcnow()
    
    await log_audit_pg(
        session, "order", order_id, "gm_reject", current_user,
        f"رفض المدير العام لأمر الشراء: {order.order_number} - السبب: {reject_data.reason}"
    )
    
    await session.commit()
    
    return {"message": "تم رفض أمر الشراء", "status": "rejected_by_gm"}


@pg_orders_router.post("/purchase-orders/{order_id}/print")
async def print_purchase_order(
    order_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Mark order as printed - printer role"""
    if current_user.role not in [UserRole.PRINTER, UserRole.PROCUREMENT_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.status != "approved":
        raise HTTPException(status_code=400, detail="أمر الشراء غير معتمد بعد")
    
    now = datetime.utcnow()
    order.status = "printed"
    order.printed_at = now
    order.updated_at = now
    
    await log_audit_pg(
        session, "order", order_id, "print", current_user,
        f"طباعة أمر الشراء: {order.order_number}"
    )
    
    await session.commit()
    
    return {"message": "تم تسجيل الطباعة بنجاح", "status": "printed"}


@pg_orders_router.post("/purchase-orders/{order_id}/ship")
async def ship_purchase_order(
    order_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Mark order as shipped"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.DELIVERY_TRACKER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.status != "printed":
        raise HTTPException(status_code=400, detail="يجب طباعة أمر الشراء أولاً")
    
    now = datetime.utcnow()
    order.status = "shipped"
    order.shipped_at = now
    order.updated_at = now
    
    await log_audit_pg(
        session, "order", order_id, "ship", current_user,
        f"شحن أمر الشراء: {order.order_number}"
    )
    
    await session.commit()
    
    return {"message": "تم تسجيل الشحن بنجاح", "status": "shipped"}


@pg_orders_router.post("/purchase-orders/{order_id}/deliver")
async def deliver_purchase_order(
    order_id: str,
    delivery_data: dict = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Mark order as delivered"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.DELIVERY_TRACKER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.status not in ["shipped", "printed", "partially_delivered"]:
        raise HTTPException(status_code=400, detail="حالة أمر الشراء لا تسمح بتسجيل التسليم")
    
    now = datetime.utcnow()
    order.status = "delivered"
    order.delivered_at = now
    order.updated_at = now
    
    if delivery_data:
        order.delivery_notes = delivery_data.get("notes")
        order.supplier_receipt_number = delivery_data.get("receipt_number")
        order.received_by_id = current_user.id
        order.received_by_name = current_user.name
    
    await log_audit_pg(
        session, "order", order_id, "deliver", current_user,
        f"تسليم أمر الشراء: {order.order_number}"
    )
    
    await session.commit()
    
    return {"message": "تم تسجيل التسليم بنجاح", "status": "delivered"}


@pg_orders_router.put("/purchase-orders/{order_id}/supplier-invoice")
async def update_supplier_invoice(
    order_id: str,
    invoice_data: dict,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """تحديث رقم فاتورة المورد - متتبع التسليم فقط"""
    if current_user.role != UserRole.DELIVERY_TRACKER:
        raise HTTPException(status_code=403, detail="فقط متتبع التسليم يمكنه تعديل رقم فاتورة المورد")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    invoice_number = invoice_data.get("supplier_invoice_number")
    if invoice_number:
        order.supplier_invoice_number = invoice_number
        order.updated_at = datetime.utcnow()
        
        await log_audit_pg(
            session, "order", order_id, "update_invoice", current_user,
            f"تحديث رقم فاتورة المورد: {invoice_number}"
        )
        
        await session.commit()
    
    return {"message": "تم تحديث رقم فاتورة المورد بنجاح"}


class UpdateOrderItemCatalog(BaseModel):
    """Schema for updating order item catalog link"""
    catalog_item_id: Optional[str] = None


@pg_orders_router.put("/purchase-orders/{order_id}/items/{item_id}/catalog-link")
async def update_order_item_catalog_link(
    order_id: str,
    item_id: str,
    update_data: UpdateOrderItemCatalog,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """تحديث ربط صنف أمر الشراء بكتالوج الأسعار - مدير المشتريات فقط"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل ربط الكتالوج")
    
    # Verify order exists and is not GM approved
    order_result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.gm_approved_by:
        raise HTTPException(status_code=400, detail="لا يمكن تعديل أمر شراء موافق عليه من المدير العام")
    
    # Get order item
    item_result = await session.execute(
        select(PurchaseOrderItem).where(
            PurchaseOrderItem.id == item_id,
            PurchaseOrderItem.order_id == order_id
        )
    )
    order_item = item_result.scalar_one_or_none()
    
    if not order_item:
        raise HTTPException(status_code=404, detail="الصنف غير موجود في أمر الشراء")
    
    # Get catalog item info if provided
    item_code = None
    if update_data.catalog_item_id:
        catalog_result = await session.execute(
            select(PriceCatalogItem).where(PriceCatalogItem.id == update_data.catalog_item_id)
        )
        catalog_item = catalog_result.scalar_one_or_none()
        if not catalog_item:
            raise HTTPException(status_code=404, detail="صنف الكتالوج غير موجود")
        item_code = catalog_item.item_code
    
    # Update the order item
    old_catalog_id = order_item.catalog_item_id
    order_item.catalog_item_id = update_data.catalog_item_id
    order_item.item_code = item_code
    order.updated_at = datetime.utcnow()
    
    await log_audit_pg(
        session, "order_item", item_id, "update_catalog_link", current_user,
        f"تحديث ربط الصنف '{order_item.name}' بالكتالوج: {item_code or 'غير مرتبط'}",
        {"old_catalog_id": old_catalog_id, "new_catalog_id": update_data.catalog_item_id}
    )
    
    await session.commit()
    
    return {
        "message": "تم تحديث ربط الصنف بالكتالوج بنجاح",
        "item_id": item_id,
        "catalog_item_id": update_data.catalog_item_id,
        "item_code": item_code
    }


# ==================== GM DASHBOARD ROUTES ====================

@pg_orders_router.get("/gm/pending-orders")
async def get_gm_pending_orders(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get orders pending GM approval"""
    if current_user.role != UserRole.GENERAL_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.status == "pending_gm_approval")
        .order_by(desc(PurchaseOrder.created_at))
    )
    orders = result.scalars().all()
    
    response = []
    for order in orders:
        items_result = await session.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.order_id == order.id)
            .order_by(PurchaseOrderItem.item_index)
        )
        items = items_result.scalars().all()
        
        response.append({
            "id": order.id,
            "order_number": order.order_number,
            "request_number": order.request_number,
            "project_name": order.project_name,
            "supplier_name": order.supplier_name,
            "category_name": order.category_name,
            "total_amount": order.total_amount,
            "status": order.status,
            "manager_name": order.manager_name,
            "supervisor_name": order.supervisor_name,
            "engineer_name": order.engineer_name,
            "notes": order.notes,
            "terms_conditions": order.terms_conditions,
            "expected_delivery_date": order.expected_delivery_date,
            "items_count": len(items),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in items
            ]
        })
    
    return response


@pg_orders_router.get("/gm/all-orders")
async def get_gm_all_orders(
    approval_type: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all orders for GM dashboard - filterable by approval type"""
    if current_user.role != UserRole.GENERAL_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    query = select(PurchaseOrder)
    
    if approval_type == "gm_approved":
        query = query.where(PurchaseOrder.gm_approved_by.isnot(None))
    elif approval_type == "manager_approved":
        query = query.where(
            and_(
                PurchaseOrder.approved_by.isnot(None),
                PurchaseOrder.gm_approved_by.is_(None)
            )
        )
    elif approval_type == "pending":
        query = query.where(PurchaseOrder.status == "pending_gm_approval")
    
    query = query.order_by(desc(PurchaseOrder.created_at))
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    response = []
    for order in orders:
        # Fetch order items for PDF export
        items_result = await session.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.order_id == order.id)
            .order_by(PurchaseOrderItem.item_index)
        )
        items = items_result.scalars().all()
        
        response.append({
            "id": order.id,
            "order_number": order.order_number,
            "request_number": order.request_number,
            "project_name": order.project_name,
            "supplier_name": order.supplier_name,
            "category_name": order.category_name,
            "total_amount": order.total_amount,
            "status": order.status,
            "manager_name": order.manager_name,
            "supervisor_name": order.supervisor_name,
            "engineer_name": order.engineer_name,
            "approved_by_name": order.approved_by_name,
            "gm_approved_by_name": order.gm_approved_by_name,
            "notes": order.notes,
            "terms_conditions": order.terms_conditions,
            "expected_delivery_date": order.expected_delivery_date,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "approved_at": order.approved_at.isoformat() if order.approved_at else None,
            "gm_approved_at": order.gm_approved_at.isoformat() if order.gm_approved_at else None,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in items
            ]
        })
    
    return response

"""
PostgreSQL Delivery Tracker Routes
APIs for delivery tracking dashboard
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
    User, DeliveryRecord, AuditLog
)

# Create router
pg_delivery_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Delivery Tracker"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


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


# ==================== DELIVERY TRACKER ROUTES ====================

@pg_delivery_router.get("/delivery-tracker/stats")
async def get_delivery_stats(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get delivery statistics for dashboard"""
    if current_user.role != UserRole.DELIVERY_TRACKER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Count orders by status
    pending_query = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status.in_(["approved", "printed", "shipped"])
    )
    pending_result = await session.execute(pending_query)
    pending_delivery = pending_result.scalar() or 0
    
    partial_query = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status == "partially_delivered"
    )
    partial_result = await session.execute(partial_query)
    partially_delivered = partial_result.scalar() or 0
    
    delivered_query = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status == "delivered"
    )
    delivered_result = await session.execute(delivered_query)
    delivered = delivered_result.scalar() or 0
    
    shipped_query = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status == "shipped"
    )
    shipped_result = await session.execute(shipped_query)
    shipped = shipped_result.scalar() or 0
    
    return {
        "pending_delivery": pending_delivery,
        "partially_delivered": partially_delivered,
        "delivered": delivered,
        "shipped": shipped
    }


@pg_delivery_router.get("/delivery-tracker/orders")
async def get_delivery_orders(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get orders for delivery tracker"""
    if current_user.role != UserRole.DELIVERY_TRACKER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Build query - only show orders ready for delivery or being tracked
    query = select(PurchaseOrder).where(
        PurchaseOrder.status.in_(["approved", "printed", "shipped", "partially_delivered", "delivered"])
    )
    
    if status:
        if status == "pending":
            query = select(PurchaseOrder).where(
                PurchaseOrder.status.in_(["approved", "printed", "shipped", "partially_delivered"])
            )
        elif status == "delivered":
            query = select(PurchaseOrder).where(PurchaseOrder.status == "delivered")
    
    query = query.order_by(desc(PurchaseOrder.created_at))
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    response = []
    for order in orders:
        # Get order items
        items_result = await session.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.order_id == order.id)
            .order_by(PurchaseOrderItem.item_index)
        )
        items = items_result.scalars().all()
        
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
            "manager_name": order.manager_name,
            "supervisor_name": order.supervisor_name,
            "engineer_name": order.engineer_name,
            "status": order.status,
            "total_amount": order.total_amount,
            "notes": order.notes,
            "supplier_receipt_number": order.supplier_receipt_number,
            "supplier_invoice_number": order.supplier_invoice_number,
            "received_by_name": order.received_by_name,
            "delivery_notes": order.delivery_notes,
            "expected_delivery_date": order.expected_delivery_date,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
        })
    
    return response


class ConfirmReceiptData(BaseModel):
    supplier_receipt_number: str
    items: List[dict]  # [{item_id, quantity_delivered}]
    notes: Optional[str] = None


@pg_delivery_router.put("/delivery-tracker/orders/{order_id}/confirm-receipt")
async def confirm_receipt(
    order_id: str,
    receipt_data: ConfirmReceiptData,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Confirm receipt of items - delivery tracker only"""
    if current_user.role != UserRole.DELIVERY_TRACKER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    if order.status not in ["approved", "printed", "shipped", "partially_delivered"]:
        raise HTTPException(status_code=400, detail="حالة أمر الشراء لا تسمح بتسجيل الاستلام")
    
    now = datetime.utcnow()
    
    # Update supplier receipt number
    order.supplier_receipt_number = receipt_data.supplier_receipt_number
    order.delivery_notes = receipt_data.notes
    order.received_by_id = current_user.id
    order.received_by_name = current_user.name
    
    # Get order items
    items_result = await session.execute(
        select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order_id)
    )
    items = items_result.scalars().all()
    items_map = {item.id: item for item in items}
    
    # Update delivered quantities
    all_fully_delivered = True
    for delivery_item in receipt_data.items:
        item_id = delivery_item.get("item_id")
        quantity_delivered = delivery_item.get("quantity_delivered", 0)
        
        if item_id in items_map:
            item = items_map[item_id]
            item.delivered_quantity += quantity_delivered
            
            if item.delivered_quantity < item.quantity:
                all_fully_delivered = False
    
    # Update order status
    if all_fully_delivered:
        order.status = "delivered"
        order.delivered_at = now
    else:
        order.status = "partially_delivered"
    
    order.updated_at = now
    
    # Create delivery record
    delivery_record = DeliveryRecord(
        id=str(uuid.uuid4()),
        order_id=order_id,
        items_delivered=json.dumps(receipt_data.items),
        delivery_date=now.isoformat(),
        delivered_by=order.supplier_name,
        received_by=current_user.name,
        notes=receipt_data.notes
    )
    session.add(delivery_record)
    
    await log_audit_pg(
        session, "delivery", order_id, "confirm_receipt", current_user,
        f"تأكيد استلام أمر الشراء: {order.order_number}"
    )
    
    await session.commit()
    
    return {
        "message": "تم تأكيد الاستلام بنجاح",
        "status": order.status,
        "fully_delivered": all_fully_delivered
    }

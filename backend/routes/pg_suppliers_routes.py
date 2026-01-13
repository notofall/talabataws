"""
PostgreSQL Suppliers Routes - Supplier Management
Migrated from MongoDB to PostgreSQL
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
import uuid

from database import get_postgres_session, Supplier, User, PurchaseOrder

# Create router
pg_suppliers_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Suppliers"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


# ==================== SUPPLIERS ROUTES ====================

@pg_suppliers_router.post("/suppliers")
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new supplier - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة الموردين")
    
    supplier_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    new_supplier = Supplier(
        id=supplier_id,
        name=supplier_data.name,
        contact_person=supplier_data.contact_person,
        phone=supplier_data.phone,
        email=supplier_data.email,
        address=supplier_data.address,
        notes=supplier_data.notes,
        created_at=now
    )
    
    session.add(new_supplier)
    await session.commit()
    
    return {
        "id": supplier_id,
        "name": supplier_data.name,
        "contact_person": supplier_data.contact_person,
        "phone": supplier_data.phone,
        "email": supplier_data.email,
        "address": supplier_data.address,
        "notes": supplier_data.notes,
        "created_at": now.isoformat()
    }


@pg_suppliers_router.get("/suppliers")
async def get_suppliers(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all suppliers"""
    result = await session.execute(
        select(Supplier).order_by(desc(Supplier.created_at))
    )
    suppliers = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "contact_person": s.contact_person,
            "phone": s.phone,
            "email": s.email,
            "address": s.address,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in suppliers
    ]


@pg_suppliers_router.get("/suppliers/{supplier_id}")
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single supplier by ID"""
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    
    # Get supplier stats
    order_result = await session.execute(
        select(
            func.count().label('count'),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label('total')
        ).select_from(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id)
    )
    stats = order_result.first()
    
    return {
        "id": supplier.id,
        "name": supplier.name,
        "contact_person": supplier.contact_person,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "notes": supplier.notes,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
        "total_orders": stats.count if stats else 0,
        "total_value": float(stats.total) if stats else 0
    }


@pg_suppliers_router.put("/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: str,
    update_data: SupplierUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a supplier - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل الموردين")
    
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    
    if update_data.name is not None:
        supplier.name = update_data.name
    if update_data.contact_person is not None:
        supplier.contact_person = update_data.contact_person
    if update_data.phone is not None:
        supplier.phone = update_data.phone
    if update_data.email is not None:
        supplier.email = update_data.email
    if update_data.address is not None:
        supplier.address = update_data.address
    if update_data.notes is not None:
        supplier.notes = update_data.notes
    
    await session.commit()
    
    return {"message": "تم تحديث المورد بنجاح"}


@pg_suppliers_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a supplier - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف الموردين")
    
    # Check if supplier has orders
    order_result = await session.execute(
        select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id)
    )
    order_count = order_result.scalar() or 0
    
    if order_count > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف المورد لوجود {order_count} أوامر شراء مرتبطة به")
    
    result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="المورد غير موجود")
    
    await session.delete(supplier)
    await session.commit()
    
    return {"message": "تم حذف المورد بنجاح"}

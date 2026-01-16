"""
PostgreSQL System Admin Routes - Backup, Restore, Company Settings
For System Admin role only
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
import json
import io
import base64

from database import (
    get_postgres_session, User, Project, Supplier, BudgetCategory,
    DefaultBudgetCategory, MaterialRequest, MaterialRequestItem,
    PurchaseOrder, PurchaseOrderItem, DeliveryRecord, AuditLog,
    SystemSetting, PriceCatalogItem, ItemAlias, Attachment
)

# Create router
pg_sysadmin_router = APIRouter(prefix="/api/pg/sysadmin", tags=["PostgreSQL System Admin"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    company_logo: Optional[str] = None  # Base64 encoded image
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    report_header: Optional[str] = None
    report_footer: Optional[str] = None
    pdf_primary_color: Optional[str] = None
    pdf_show_logo: Optional[bool] = None


# ==================== HELPER ====================

def require_system_admin(current_user: User):
    """Check if user is system admin"""
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="فقط مدير النظام يمكنه الوصول لهذه الصفحة")


# ==================== COMPANY SETTINGS ====================

@pg_sysadmin_router.get("/company-settings")
async def get_company_settings(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get company settings for PDF customization - System Admin only"""
    require_system_admin(current_user)
    
    # Define company setting keys
    setting_keys = [
        "company_name", "company_logo", "company_address", "company_phone",
        "company_email", "report_header", "report_footer", "pdf_primary_color", "pdf_show_logo"
    ]
    
    settings = {}
    for key in setting_keys:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        settings[key] = setting.value if setting else ""
    
    return settings


@pg_sysadmin_router.get("/company-settings/public")
async def get_company_settings_public(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get company settings for PDF customization - Available for all authenticated users"""
    # Define company setting keys
    setting_keys = [
        "company_name", "company_logo", "company_address", "company_phone",
        "company_email", "report_header", "report_footer", "pdf_primary_color", "pdf_show_logo"
    ]
    
    settings = {}
    for key in setting_keys:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        settings[key] = setting.value if setting else ""
    
    return settings


@pg_sysadmin_router.put("/company-settings")
async def update_company_settings(
    settings_data: CompanySettingsUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update company settings"""
    require_system_admin(current_user)
    
    now = datetime.utcnow()
    updates = settings_data.dict(exclude_none=True)
    
    for key, value in updates.items():
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = str(value)
            setting.updated_by = current_user.id
            setting.updated_by_name = current_user.name
            setting.updated_at = now
        else:
            new_setting = SystemSetting(
                id=str(uuid.uuid4()),
                key=key,
                value=str(value),
                description=f"إعداد الشركة: {key}",
                updated_by=current_user.id,
                updated_by_name=current_user.name,
                created_at=now
            )
            session.add(new_setting)
    
    await session.commit()
    
    return {"message": "تم تحديث إعدادات الشركة بنجاح"}


@pg_sysadmin_router.post("/company-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Upload company logo"""
    require_system_admin(current_user)
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="يجب رفع ملف صورة")
    
    # Read and encode image
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2MB limit
        raise HTTPException(status_code=400, detail="حجم الصورة يجب أن يكون أقل من 2 ميغابايت")
    
    base64_image = base64.b64encode(content).decode('utf-8')
    logo_data = f"data:{file.content_type};base64,{base64_image}"
    
    now = datetime.utcnow()
    
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "company_logo")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = logo_data
        setting.updated_by = current_user.id
        setting.updated_by_name = current_user.name
        setting.updated_at = now
    else:
        new_setting = SystemSetting(
            id=str(uuid.uuid4()),
            key="company_logo",
            value=logo_data,
            description="شعار الشركة",
            updated_by=current_user.id,
            updated_by_name=current_user.name,
            created_at=now
        )
        session.add(new_setting)
    
    await session.commit()
    
    return {"message": "تم رفع الشعار بنجاح", "logo": logo_data}


# ==================== BACKUP & RESTORE ====================

@pg_sysadmin_router.get("/backup")
async def create_backup(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a full system backup as JSON"""
    require_system_admin(current_user)
    
    backup_data = {
        "backup_info": {
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user.name,
            "version": "1.0"
        },
        "users": [],
        "projects": [],
        "suppliers": [],
        "budget_categories": [],
        "default_budget_categories": [],
        "material_requests": [],
        "material_request_items": [],
        "purchase_orders": [],
        "purchase_order_items": [],
        "delivery_records": [],
        "system_settings": [],
        "audit_logs": []
    }
    
    # Export Users
    result = await session.execute(select(User))
    for u in result.scalars().all():
        backup_data["users"].append({
            "id": u.id, "name": u.name, "email": u.email, "password": u.password,
            "role": u.role, "is_active": u.is_active, "supervisor_prefix": u.supervisor_prefix,
            "assigned_projects": u.assigned_projects, "assigned_engineers": u.assigned_engineers,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    
    # Export Projects
    result = await session.execute(select(Project))
    for p in result.scalars().all():
        backup_data["projects"].append({
            "id": p.id, "name": p.name, "owner_name": p.owner_name, "description": p.description,
            "location": p.location, "status": p.status, "created_by": p.created_by,
            "created_by_name": p.created_by_name, "created_at": p.created_at.isoformat() if p.created_at else None
        })
    
    # Export Suppliers
    result = await session.execute(select(Supplier))
    for s in result.scalars().all():
        backup_data["suppliers"].append({
            "id": s.id, "name": s.name, "contact_person": s.contact_person, "phone": s.phone,
            "email": s.email, "address": s.address, "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    
    # Export Budget Categories
    result = await session.execute(select(BudgetCategory))
    for c in result.scalars().all():
        backup_data["budget_categories"].append({
            "id": c.id, "name": c.name, "project_id": c.project_id, "project_name": c.project_name,
            "estimated_budget": c.estimated_budget, "created_by": c.created_by,
            "created_by_name": c.created_by_name, "created_at": c.created_at.isoformat() if c.created_at else None
        })
    
    # Export Default Budget Categories
    result = await session.execute(select(DefaultBudgetCategory))
    for c in result.scalars().all():
        backup_data["default_budget_categories"].append({
            "id": c.id, "name": c.name, "default_budget": c.default_budget, "created_by": c.created_by,
            "created_by_name": c.created_by_name, "created_at": c.created_at.isoformat() if c.created_at else None
        })
    
    # Export Material Requests
    result = await session.execute(select(MaterialRequest))
    for r in result.scalars().all():
        backup_data["material_requests"].append({
            "id": r.id, "request_number": r.request_number, "request_seq": r.request_seq,
            "project_id": r.project_id, "project_name": r.project_name, "reason": r.reason,
            "supervisor_id": r.supervisor_id, "supervisor_name": r.supervisor_name,
            "engineer_id": r.engineer_id, "engineer_name": r.engineer_name, "status": r.status,
            "rejection_reason": r.rejection_reason, "expected_delivery_date": r.expected_delivery_date,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    # Export Material Request Items
    result = await session.execute(select(MaterialRequestItem))
    for i in result.scalars().all():
        backup_data["material_request_items"].append({
            "id": i.id, "request_id": i.request_id, "name": i.name, "quantity": i.quantity,
            "unit": i.unit, "estimated_price": i.estimated_price, "item_index": i.item_index
        })
    
    # Export Purchase Orders
    result = await session.execute(select(PurchaseOrder))
    for o in result.scalars().all():
        backup_data["purchase_orders"].append({
            "id": o.id, "order_number": o.order_number, "order_seq": o.order_seq,
            "request_id": o.request_id, "request_number": o.request_number,
            "project_id": o.project_id, "project_name": o.project_name,
            "supplier_id": o.supplier_id, "supplier_name": o.supplier_name,
            "category_id": o.category_id, "category_name": o.category_name,
            "manager_id": o.manager_id, "manager_name": o.manager_name,
            "supervisor_name": o.supervisor_name, "engineer_name": o.engineer_name,
            "status": o.status, "needs_gm_approval": o.needs_gm_approval,
            "approved_by": o.approved_by, "approved_by_name": o.approved_by_name,
            "gm_approved_by": o.gm_approved_by, "gm_approved_by_name": o.gm_approved_by_name,
            "total_amount": o.total_amount, "notes": o.notes, "terms_conditions": o.terms_conditions,
            "expected_delivery_date": o.expected_delivery_date,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "approved_at": o.approved_at.isoformat() if o.approved_at else None
        })
    
    # Export Purchase Order Items
    result = await session.execute(select(PurchaseOrderItem))
    for i in result.scalars().all():
        backup_data["purchase_order_items"].append({
            "id": i.id, "order_id": i.order_id, "name": i.name, "quantity": i.quantity,
            "unit": i.unit, "unit_price": i.unit_price, "total_price": i.total_price,
            "delivered_quantity": i.delivered_quantity, "item_index": i.item_index
        })
    
    # Export System Settings
    result = await session.execute(select(SystemSetting))
    for s in result.scalars().all():
        backup_data["system_settings"].append({
            "id": s.id, "key": s.key, "value": s.value, "description": s.description
        })
    
    # Create JSON file
    json_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
    
    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(json_content.encode('utf-8')),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@pg_sysadmin_router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Restore system from backup file"""
    require_system_admin(current_user)
    
    try:
        content = await file.read()
        backup_data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="ملف النسخة الاحتياطية غير صالح")
    
    if "backup_info" not in backup_data:
        raise HTTPException(status_code=400, detail="ملف النسخة الاحتياطية غير صالح")
    
    restored_counts = {
        "users": 0, "projects": 0, "suppliers": 0, "budget_categories": 0,
        "material_requests": 0, "purchase_orders": 0
    }
    
    try:
        # Restore Users (skip if already exists)
        for u_data in backup_data.get("users", []):
            result = await session.execute(select(User).where(User.id == u_data["id"]))
            if result.scalar_one_or_none():
                continue
            user = User(**{k: v for k, v in u_data.items() if k != "created_at"})
            if u_data.get("created_at"):
                user.created_at = datetime.fromisoformat(u_data["created_at"])
            session.add(user)
            restored_counts["users"] += 1
        
        # Restore Projects
        for p_data in backup_data.get("projects", []):
            result = await session.execute(select(Project).where(Project.id == p_data["id"]))
            if result.scalar_one_or_none():
                continue
            project = Project(**{k: v for k, v in p_data.items() if k not in ["created_at", "updated_at"]})
            if p_data.get("created_at"):
                project.created_at = datetime.fromisoformat(p_data["created_at"])
            session.add(project)
            restored_counts["projects"] += 1
        
        # Restore Suppliers
        for s_data in backup_data.get("suppliers", []):
            result = await session.execute(select(Supplier).where(Supplier.id == s_data["id"]))
            if result.scalar_one_or_none():
                continue
            supplier = Supplier(**{k: v for k, v in s_data.items() if k != "created_at"})
            if s_data.get("created_at"):
                supplier.created_at = datetime.fromisoformat(s_data["created_at"])
            session.add(supplier)
            restored_counts["suppliers"] += 1
        
        # Restore Budget Categories
        for c_data in backup_data.get("budget_categories", []):
            result = await session.execute(select(BudgetCategory).where(BudgetCategory.id == c_data["id"]))
            if result.scalar_one_or_none():
                continue
            category = BudgetCategory(**{k: v for k, v in c_data.items() if k != "created_at"})
            if c_data.get("created_at"):
                category.created_at = datetime.fromisoformat(c_data["created_at"])
            session.add(category)
            restored_counts["budget_categories"] += 1
        
        # Restore Material Requests
        for r_data in backup_data.get("material_requests", []):
            result = await session.execute(select(MaterialRequest).where(MaterialRequest.id == r_data["id"]))
            if result.scalar_one_or_none():
                continue
            request = MaterialRequest(**{k: v for k, v in r_data.items() if k not in ["created_at", "updated_at"]})
            if r_data.get("created_at"):
                request.created_at = datetime.fromisoformat(r_data["created_at"])
            session.add(request)
            restored_counts["material_requests"] += 1
        
        # Restore Material Request Items
        for i_data in backup_data.get("material_request_items", []):
            result = await session.execute(select(MaterialRequestItem).where(MaterialRequestItem.id == i_data["id"]))
            if result.scalar_one_or_none():
                continue
            item = MaterialRequestItem(**i_data)
            session.add(item)
        
        # Restore Purchase Orders
        for o_data in backup_data.get("purchase_orders", []):
            result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == o_data["id"]))
            if result.scalar_one_or_none():
                continue
            order = PurchaseOrder(**{k: v for k, v in o_data.items() if k not in ["created_at", "approved_at", "updated_at"]})
            if o_data.get("created_at"):
                order.created_at = datetime.fromisoformat(o_data["created_at"])
            if o_data.get("approved_at"):
                order.approved_at = datetime.fromisoformat(o_data["approved_at"])
            session.add(order)
            restored_counts["purchase_orders"] += 1
        
        # Restore Purchase Order Items
        for i_data in backup_data.get("purchase_order_items", []):
            result = await session.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.id == i_data["id"]))
            if result.scalar_one_or_none():
                continue
            item = PurchaseOrderItem(**i_data)
            session.add(item)
        
        # Restore System Settings
        for s_data in backup_data.get("system_settings", []):
            result = await session.execute(select(SystemSetting).where(SystemSetting.key == s_data["key"]))
            if result.scalar_one_or_none():
                continue
            setting = SystemSetting(**s_data)
            session.add(setting)
        
        await session.commit()
        
        return {
            "message": "تم استعادة النسخة الاحتياطية بنجاح",
            "restored": restored_counts
        }
    
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"خطأ في استعادة النسخة الاحتياطية: {str(e)}")


# ==================== DATA CLEANUP ====================

@pg_sysadmin_router.delete("/delete-order/{order_id}")
async def delete_order_sysadmin(
    order_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a purchase order - system admin only"""
    require_system_admin(current_user)
    
    result = await session.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="أمر الشراء غير موجود")
    
    order_number = order.order_number
    
    # Delete order items first
    await session.execute(
        PurchaseOrderItem.__table__.delete().where(PurchaseOrderItem.order_id == order_id)
    )
    
    await session.delete(order)
    
    # Log audit
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        entity_type="order",
        entity_id=order_id,
        action="delete",
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        description=f"حذف أمر الشراء: {order_number}"
    )
    session.add(audit_log)
    
    await session.commit()
    
    return {"message": f"تم حذف أمر الشراء {order_number} بنجاح"}


@pg_sysadmin_router.post("/clean-data")
async def clean_all_data_sysadmin(
    preserve_admin_email: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Clean all data except specified admin - system admin only"""
    require_system_admin(current_user)
    
    # Delete in order (respecting foreign keys)
    await session.execute(PurchaseOrderItem.__table__.delete())
    await session.execute(DeliveryRecord.__table__.delete())
    await session.execute(PurchaseOrder.__table__.delete())
    await session.execute(MaterialRequestItem.__table__.delete())
    await session.execute(MaterialRequest.__table__.delete())
    await session.execute(BudgetCategory.__table__.delete())
    await session.execute(Project.__table__.delete())
    await session.execute(ItemAlias.__table__.delete())
    await session.execute(PriceCatalogItem.__table__.delete())
    await session.execute(Supplier.__table__.delete())
    await session.execute(Attachment.__table__.delete())
    await session.execute(AuditLog.__table__.delete())
    
    # Delete users except the preserved admin
    await session.execute(
        User.__table__.delete().where(User.email != preserve_admin_email)
    )
    
    await session.commit()
    
    return {"message": "تم تنظيف جميع البيانات بنجاح"}


# ==================== STATS & DASHBOARD ====================

@pg_sysadmin_router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get system statistics - system admin only"""
    require_system_admin(current_user)
    
    # Count all entities
    users_count = (await session.execute(select(func.count()).select_from(User))).scalar()
    projects_count = (await session.execute(select(func.count()).select_from(Project))).scalar()
    suppliers_count = (await session.execute(select(func.count()).select_from(Supplier))).scalar()
    requests_count = (await session.execute(select(func.count()).select_from(MaterialRequest))).scalar()
    orders_count = (await session.execute(select(func.count()).select_from(PurchaseOrder))).scalar()
    
    # Total order amount
    total_amount_result = await session.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
    )
    total_amount = float(total_amount_result.scalar() or 0)
    
    return {
        "users_count": users_count,
        "projects_count": projects_count,
        "suppliers_count": suppliers_count,
        "requests_count": requests_count,
        "orders_count": orders_count,
        "total_amount": total_amount
    }

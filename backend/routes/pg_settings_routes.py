"""
PostgreSQL System Settings & Reports Routes
Migrated from MongoDB to PostgreSQL
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_
import uuid
import json

from database import (
    get_postgres_session, SystemSetting, AuditLog, User,
    PurchaseOrder, Project, BudgetCategory, Supplier
)

# Create router
pg_settings_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Settings & Reports"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class SystemSettingUpdate(BaseModel):
    value: str


# ==================== SYSTEM SETTINGS ROUTES ====================

@pg_settings_router.get("/settings")
async def get_system_settings(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all system settings - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(select(SystemSetting))
    settings = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "key": s.key,
            "value": s.value,
            "description": s.description,
            "updated_by_name": s.updated_by_name,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }
        for s in settings
    ]


@pg_settings_router.get("/settings/{key}")
async def get_system_setting(
    key: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single system setting"""
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="الإعداد غير موجود")
    
    return {
        "key": setting.key,
        "value": setting.value,
        "description": setting.description
    }


@pg_settings_router.put("/settings/{key}")
async def update_system_setting(
    key: str,
    update_data: SystemSettingUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a system setting - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="الإعداد غير موجود")
    
    old_value = setting.value
    setting.value = update_data.value
    setting.updated_by = current_user.id
    setting.updated_by_name = current_user.name
    setting.updated_at = datetime.utcnow()
    
    # Log audit
    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        entity_type="setting",
        entity_id=setting.id,
        action="update",
        changes=json.dumps({"old": old_value, "new": update_data.value}),
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        description=f"تحديث الإعداد: {key}"
    )
    session.add(audit_log)
    
    await session.commit()
    
    return {"message": "تم تحديث الإعداد بنجاح"}


@pg_settings_router.post("/settings/init")
async def init_system_settings(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Initialize default system settings - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    default_settings = [
        {"key": "approval_limit", "value": "20000", "description": "حد الموافقة - المبالغ الأعلى تحتاج موافقة المدير العام"},
        {"key": "company_name", "value": "شركة المشتريات", "description": "اسم الشركة"},
        {"key": "company_address", "value": "", "description": "عنوان الشركة"},
        {"key": "company_phone", "value": "", "description": "هاتف الشركة"},
        {"key": "company_email", "value": "", "description": "البريد الإلكتروني للشركة"},
        {"key": "currency", "value": "ريال سعودي", "description": "العملة المستخدمة"},
        {"key": "vat_rate", "value": "15", "description": "نسبة ضريبة القيمة المضافة"},
    ]
    
    now = datetime.utcnow()
    added = 0
    
    for setting_data in default_settings:
        # Check if exists
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == setting_data["key"])
        )
        if result.scalar_one_or_none():
            continue
        
        setting = SystemSetting(
            id=str(uuid.uuid4()),
            key=setting_data["key"],
            value=setting_data["value"],
            description=setting_data["description"],
            updated_by=current_user.id,
            updated_by_name=current_user.name,
            created_at=now
        )
        session.add(setting)
        added += 1
    
    await session.commit()
    
    return {"message": f"تم إضافة {added} إعداد", "added_count": added}


# ==================== REPORTS ROUTES ====================

@pg_settings_router.get("/reports/cost-savings")
async def get_cost_savings_report(
    project_id: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get cost savings report"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    query = select(PurchaseOrder).where(PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"]))
    
    if project_id:
        query = query.where(PurchaseOrder.project_id == project_id)
    if category_id:
        query = query.where(PurchaseOrder.category_id == category_id)
    if start_date:
        query = query.where(PurchaseOrder.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.where(PurchaseOrder.created_at <= datetime.fromisoformat(end_date))
    
    result = await session.execute(query)
    orders = result.scalars().all()
    
    # Group by project
    by_project = {}
    for order in orders:
        project_name = order.project_name
        if project_name not in by_project:
            by_project[project_name] = {
                "project_name": project_name,
                "total_amount": 0,
                "order_count": 0
            }
        by_project[project_name]["total_amount"] += order.total_amount
        by_project[project_name]["order_count"] += 1
    
    # Group by category
    by_category = {}
    for order in orders:
        category_name = order.category_name or "غير مصنف"
        if category_name not in by_category:
            by_category[category_name] = {
                "category_name": category_name,
                "total_amount": 0,
                "order_count": 0
            }
        by_category[category_name]["total_amount"] += order.total_amount
        by_category[category_name]["order_count"] += 1
    
    # Group by supplier
    by_supplier = {}
    for order in orders:
        supplier_name = order.supplier_name
        if supplier_name not in by_supplier:
            by_supplier[supplier_name] = {
                "supplier_name": supplier_name,
                "total_amount": 0,
                "order_count": 0
            }
        by_supplier[supplier_name]["total_amount"] += order.total_amount
        by_supplier[supplier_name]["order_count"] += 1
    
    total_amount = sum(o.total_amount for o in orders)
    
    return {
        "total_orders": len(orders),
        "total_amount": total_amount,
        "by_project": list(by_project.values()),
        "by_category": list(by_category.values()),
        "by_supplier": list(by_supplier.values())
    }


@pg_settings_router.get("/reports/dashboard")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get dashboard statistics"""
    # Total projects
    projects_result = await session.execute(
        select(func.count()).select_from(Project).where(Project.status == "active")
    )
    total_projects = projects_result.scalar() or 0
    
    # Total suppliers
    suppliers_result = await session.execute(
        select(func.count()).select_from(Supplier)
    )
    total_suppliers = suppliers_result.scalar() or 0
    
    # Orders stats
    orders_result = await session.execute(
        select(
            func.count().label('total'),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label('total_amount')
        ).select_from(PurchaseOrder)
    )
    orders_stats = orders_result.first()
    
    # Pending orders
    pending_result = await session.execute(
        select(func.count()).select_from(PurchaseOrder)
        .where(PurchaseOrder.status.in_(["pending_approval", "pending_gm_approval"]))
    )
    pending_orders = pending_result.scalar() or 0
    
    # Delivered orders
    delivered_result = await session.execute(
        select(func.count()).select_from(PurchaseOrder)
        .where(PurchaseOrder.status == "delivered")
    )
    delivered_orders = delivered_result.scalar() or 0
    
    return {
        "total_projects": total_projects,
        "total_suppliers": total_suppliers,
        "total_orders": orders_stats.total if orders_stats else 0,
        "total_amount": float(orders_stats.total_amount) if orders_stats else 0,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders
    }


@pg_settings_router.get("/reports/budget")
async def get_budget_report(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get budget report - spending by category and project"""
    
    # Get all budget categories
    categories_result = await session.execute(
        select(BudgetCategory).order_by(BudgetCategory.name)
    )
    categories = categories_result.scalars().all()
    
    # Get all projects
    projects_query = select(Project).where(Project.status == "active")
    if project_id:
        projects_query = projects_query.where(Project.id == project_id)
    projects_result = await session.execute(projects_query.order_by(Project.name))
    projects = projects_result.scalars().all()
    
    budget_data = []
    
    for project in projects:
        project_budget = {
            "project_id": project.id,
            "project_name": project.name,
            "categories": [],
            "total_spent": 0
        }
        
        # Get spending per category for this project
        for category in categories:
            # Sum of approved orders in this category for this project
            spending_result = await session.execute(
                select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
                .select_from(PurchaseOrder)
                .where(
                    PurchaseOrder.project_id == project.id,
                    PurchaseOrder.category_id == category.id,
                    PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"])
                )
            )
            spent = float(spending_result.scalar() or 0)
            
            cat_budget = float(category.budget or 0)
            
            if spent > 0 or cat_budget > 0:
                project_budget["categories"].append({
                    "category_id": category.id,
                    "category_name": category.name,
                    "budget": cat_budget,
                    "spent": spent,
                    "remaining": cat_budget - spent,
                    "percentage": round((spent / cat_budget * 100), 1) if cat_budget > 0 else 0
                })
            
            project_budget["total_spent"] += spent
        
        if project_budget["total_spent"] > 0 or project_budget["categories"]:
            budget_data.append(project_budget)
    
    # Get overall category totals
    category_totals = []
    for category in categories:
        total_budget = float(category.budget or 0)
        
        # Total spent in this category across all projects
        total_spent_result = await session.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
            .select_from(PurchaseOrder)
            .where(
                PurchaseOrder.category_id == category.id,
                PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"])
            )
        )
        total_spent = float(total_spent_result.scalar() or 0)
        
        if total_budget > 0 or total_spent > 0:
            category_totals.append({
                "category_id": category.id,
                "category_name": category.name,
                "budget": total_budget,
                "spent": total_spent,
                "remaining": total_budget - total_spent,
                "percentage": round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0
            })
    
    # Summary
    total_all_budgets = sum(c["budget"] for c in category_totals)
    total_all_spent = sum(c["spent"] for c in category_totals)
    
    return {
        "projects": budget_data,
        "categories": category_totals,
        "summary": {
            "total_budget": total_all_budgets,
            "total_spent": total_all_spent,
            "total_remaining": total_all_budgets - total_all_spent,
            "overall_percentage": round((total_all_spent / total_all_budgets * 100), 1) if total_all_budgets > 0 else 0
        }
    }


# ==================== AUDIT LOG ROUTES ====================

@pg_settings_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get audit logs - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    query = select(AuditLog)
    
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    
    query = query.order_by(desc(AuditLog.timestamp)).limit(limit)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "action": log.action,
            "description": log.description,
            "user_name": log.user_name,
            "user_role": log.user_role,
            "changes": json.loads(log.changes) if log.changes else None,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None
        }
        for log in logs
    ]

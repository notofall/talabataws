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
    PurchaseOrder, Project, BudgetCategory, Supplier, MaterialRequest
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
    """Get cost savings report - available for procurement manager and general manager"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.GENERAL_MANAGER]:
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
            "total_spent": 0,
            "total_budget": 0
        }
        
        # Get categories for this project
        project_cats_result = await session.execute(
            select(BudgetCategory).where(BudgetCategory.project_id == project.id)
        )
        project_cats = project_cats_result.scalars().all()
        
        for category in project_cats:
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
            cat_budget = float(category.estimated_budget or 0)
            
            project_budget["categories"].append({
                "category_id": category.id,
                "category_name": category.name,
                "budget": cat_budget,
                "spent": spent,
                "remaining": cat_budget - spent,
                "percentage": round((spent / cat_budget * 100), 1) if cat_budget > 0 else 0
            })
            
            project_budget["total_spent"] += spent
            project_budget["total_budget"] += cat_budget
        
        project_budget["remaining"] = project_budget["total_budget"] - project_budget["total_spent"]
        project_budget["percentage"] = round(
            (project_budget["total_spent"] / project_budget["total_budget"] * 100), 1
        ) if project_budget["total_budget"] > 0 else 0
        
        budget_data.append(project_budget)
    
    # Summary
    total_all_budgets = sum(p["total_budget"] for p in budget_data)
    total_all_spent = sum(p["total_spent"] for p in budget_data)
    
    return {
        "projects": budget_data,
        "summary": {
            "total_budget": total_all_budgets,
            "total_spent": total_all_spent,
            "total_remaining": total_all_budgets - total_all_spent,
            "overall_percentage": round((total_all_spent / total_all_budgets * 100), 1) if total_all_budgets > 0 else 0
        }
    }


# ==================== ADVANCED REPORTS ====================

@pg_settings_router.get("/reports/advanced/summary")
async def get_advanced_summary_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """ملخص تنفيذي شامل - للمدير العام ومدير المشتريات"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.GENERAL_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Date filters
    date_filter_orders = []
    date_filter_requests = []
    if start_date:
        start = datetime.fromisoformat(start_date)
        date_filter_orders.append(PurchaseOrder.created_at >= start)
        date_filter_requests.append(MaterialRequest.created_at >= start)
    if end_date:
        end = datetime.fromisoformat(end_date)
        date_filter_orders.append(PurchaseOrder.created_at <= end)
        date_filter_requests.append(MaterialRequest.created_at <= end)
    
    # Total Purchase Orders
    orders_query = select(PurchaseOrder)
    if date_filter_orders:
        orders_query = orders_query.where(and_(*date_filter_orders))
    orders_result = await session.execute(orders_query)
    all_orders = orders_result.scalars().all()
    
    # Total Material Requests
    requests_query = select(MaterialRequest)
    if date_filter_requests:
        requests_query = requests_query.where(and_(*date_filter_requests))
    requests_result = await session.execute(requests_query)
    all_requests = requests_result.scalars().all()
    
    # Order statistics
    orders_by_status = {}
    total_order_amount = 0
    for order in all_orders:
        status = order.status or "pending"
        orders_by_status[status] = orders_by_status.get(status, 0) + 1
        if order.status in ["approved", "printed", "shipped", "delivered"]:
            total_order_amount += order.total_amount or 0
    
    # Request statistics
    requests_by_status = {}
    for req in all_requests:
        status = req.status or "pending"
        requests_by_status[status] = requests_by_status.get(status, 0) + 1
    
    # Monthly spending trend (last 6 months)
    monthly_spending = []
    from datetime import timedelta
    now = datetime.utcnow()
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        month_result = await session.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
            .where(
                PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"]),
                PurchaseOrder.created_at >= month_start,
                PurchaseOrder.created_at < month_end
            )
        )
        month_total = float(month_result.scalar() or 0)
        monthly_spending.append({
            "month": month_start.strftime("%Y-%m"),
            "month_name": month_start.strftime("%B %Y"),
            "amount": month_total
        })
    
    # Top 5 projects by spending
    top_projects_result = await session.execute(
        select(
            PurchaseOrder.project_name,
            func.sum(PurchaseOrder.total_amount).label("total")
        )
        .where(PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"]))
        .group_by(PurchaseOrder.project_name)
        .order_by(desc("total"))
        .limit(5)
    )
    top_projects = [{"name": r[0], "amount": float(r[1] or 0)} for r in top_projects_result.all()]
    
    # Top 5 suppliers by amount
    top_suppliers_result = await session.execute(
        select(
            PurchaseOrder.supplier_name,
            func.sum(PurchaseOrder.total_amount).label("total"),
            func.count(PurchaseOrder.id).label("order_count")
        )
        .where(PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"]))
        .group_by(PurchaseOrder.supplier_name)
        .order_by(desc("total"))
        .limit(5)
    )
    top_suppliers = [{"name": r[0], "amount": float(r[1] or 0), "orders": r[2]} for r in top_suppliers_result.all()]
    
    # Spending by category
    by_category_result = await session.execute(
        select(
            PurchaseOrder.category_name,
            func.sum(PurchaseOrder.total_amount).label("total")
        )
        .where(PurchaseOrder.status.in_(["approved", "printed", "shipped", "delivered"]))
        .group_by(PurchaseOrder.category_name)
        .order_by(desc("total"))
    )
    spending_by_category = [{"name": r[0] or "غير مصنف", "amount": float(r[1] or 0)} for r in by_category_result.all()]
    
    return {
        "summary": {
            "total_orders": len(all_orders),
            "total_requests": len(all_requests),
            "total_spending": total_order_amount,
            "approved_orders": orders_by_status.get("approved", 0) + orders_by_status.get("printed", 0) + orders_by_status.get("shipped", 0) + orders_by_status.get("delivered", 0),
            "pending_orders": orders_by_status.get("pending", 0) + orders_by_status.get("pending_gm", 0),
            "rejected_orders": orders_by_status.get("rejected", 0) + orders_by_status.get("rejected_gm", 0)
        },
        "orders_by_status": orders_by_status,
        "requests_by_status": requests_by_status,
        "monthly_spending": monthly_spending,
        "top_projects": top_projects,
        "top_suppliers": top_suppliers,
        "spending_by_category": spending_by_category
    }


@pg_settings_router.get("/reports/advanced/approval-analytics")
async def get_approval_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """تحليل سير الاعتمادات - للمدير العام ومدير المشتريات"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.GENERAL_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    date_filter = []
    if start_date:
        date_filter.append(MaterialRequest.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        date_filter.append(MaterialRequest.created_at <= datetime.fromisoformat(end_date))
    
    # Get all requests
    query = select(MaterialRequest)
    if date_filter:
        query = query.where(and_(*date_filter))
    result = await session.execute(query)
    all_requests = result.scalars().all()
    
    # Approval statistics
    total = len(all_requests)
    approved = len([r for r in all_requests if r.status in ["approved", "po_issued"]])
    rejected = len([r for r in all_requests if r.status in ["rejected", "rejected_engineer"]])
    pending = len([r for r in all_requests if r.status in ["pending", "pending_engineer"]])
    
    # By engineer
    by_engineer = {}
    for req in all_requests:
        engineer = req.engineer_name or "غير محدد"
        if engineer not in by_engineer:
            by_engineer[engineer] = {"approved": 0, "rejected": 0, "pending": 0, "total": 0}
        by_engineer[engineer]["total"] += 1
        if req.status in ["approved", "po_issued"]:
            by_engineer[engineer]["approved"] += 1
        elif req.status in ["rejected", "rejected_engineer"]:
            by_engineer[engineer]["rejected"] += 1
        else:
            by_engineer[engineer]["pending"] += 1
    
    # By supervisor
    by_supervisor = {}
    for req in all_requests:
        supervisor = req.supervisor_name or "غير محدد"
        if supervisor not in by_supervisor:
            by_supervisor[supervisor] = {"approved": 0, "rejected": 0, "pending": 0, "total": 0}
        by_supervisor[supervisor]["total"] += 1
        if req.status in ["approved", "po_issued"]:
            by_supervisor[supervisor]["approved"] += 1
        elif req.status in ["rejected", "rejected_engineer"]:
            by_supervisor[supervisor]["rejected"] += 1
        else:
            by_supervisor[supervisor]["pending"] += 1
    
    # By project
    by_project = {}
    for req in all_requests:
        project = req.project_name or "غير محدد"
        if project not in by_project:
            by_project[project] = {"approved": 0, "rejected": 0, "pending": 0, "total": 0}
        by_project[project]["total"] += 1
        if req.status in ["approved", "po_issued"]:
            by_project[project]["approved"] += 1
        elif req.status in ["rejected", "rejected_engineer"]:
            by_project[project]["rejected"] += 1
        else:
            by_project[project]["pending"] += 1
    
    return {
        "summary": {
            "total_requests": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": round((approved / total * 100), 1) if total > 0 else 0,
            "rejection_rate": round((rejected / total * 100), 1) if total > 0 else 0
        },
        "by_engineer": [{"name": k, **v} for k, v in by_engineer.items()],
        "by_supervisor": [{"name": k, **v} for k, v in by_supervisor.items()],
        "by_project": [{"name": k, **v} for k, v in by_project.items()]
    }


@pg_settings_router.get("/reports/advanced/supplier-performance")
async def get_supplier_performance_report(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """تقرير أداء الموردين - للمدير العام ومدير المشتريات"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.GENERAL_MANAGER]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    # Get all suppliers
    suppliers_result = await session.execute(select(Supplier))
    suppliers = suppliers_result.scalars().all()
    
    performance_data = []
    
    for supplier in suppliers:
        # Orders for this supplier
        orders_result = await session.execute(
            select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier.id)
        )
        orders = orders_result.scalars().all()
        
        if not orders:
            continue
        
        total_orders = len(orders)
        completed_orders = len([o for o in orders if o.status in ["delivered"]])
        approved_orders = len([o for o in orders if o.status in ["approved", "printed", "shipped", "delivered"]])
        total_amount = sum(o.total_amount or 0 for o in orders if o.status in ["approved", "printed", "shipped", "delivered"])
        
        # On-time delivery rate (simplified - based on status)
        delivered = [o for o in orders if o.status == "delivered"]
        
        performance_data.append({
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "contact_person": supplier.contact_person,
            "phone": supplier.phone,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "approved_orders": approved_orders,
            "total_amount": total_amount,
            "completion_rate": round((completed_orders / total_orders * 100), 1) if total_orders > 0 else 0,
            "avg_order_value": round(total_amount / approved_orders, 2) if approved_orders > 0 else 0
        })
    
    # Sort by total amount
    performance_data.sort(key=lambda x: x["total_amount"], reverse=True)
    
    return {
        "suppliers": performance_data,
        "summary": {
            "total_suppliers": len(performance_data),
            "total_orders": sum(s["total_orders"] for s in performance_data),
            "total_spending": sum(s["total_amount"] for s in performance_data)
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
    """Get audit logs - system admin and procurement manager only"""
    if current_user.role not in [UserRole.PROCUREMENT_MANAGER, UserRole.SYSTEM_ADMIN]:
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

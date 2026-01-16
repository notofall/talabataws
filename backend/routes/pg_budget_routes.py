"""
PostgreSQL Budget Categories Routes
Migrated from MongoDB to PostgreSQL
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
import uuid
import json

from database import (
    get_postgres_session, BudgetCategory, DefaultBudgetCategory, 
    User, Project, PurchaseOrder, AuditLog
)

# Create router
pg_budget_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Budget Categories"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class DefaultBudgetCategoryCreate(BaseModel):
    name: str
    default_budget: float = 0


class DefaultBudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    default_budget: Optional[float] = None


class BudgetCategoryCreate(BaseModel):
    name: str
    project_id: str
    estimated_budget: float
    code: Optional[str] = None  # كود التصنيف (اختياري - يُولد تلقائياً)


class BudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    estimated_budget: Optional[float] = None


# ==================== HELPER ====================

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


# ==================== DEFAULT BUDGET CATEGORIES ====================

@pg_budget_router.get("/default-budget-categories")
async def get_default_budget_categories(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all default budget categories"""
    result = await session.execute(
        select(DefaultBudgetCategory).order_by(DefaultBudgetCategory.created_at)
    )
    categories = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "default_budget": c.default_budget,
            "created_by": c.created_by,
            "created_by_name": c.created_by_name,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in categories
    ]


@pg_budget_router.post("/default-budget-categories")
async def create_default_budget_category(
    category_data: DefaultBudgetCategoryCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a default budget category - procurement manager only"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات الافتراضية")
    
    # Check if exists
    result = await session.execute(
        select(DefaultBudgetCategory).where(DefaultBudgetCategory.name == category_data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="يوجد تصنيف بنفس الاسم")
    
    category_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_category = DefaultBudgetCategory(
        id=category_id,
        name=category_data.name,
        default_budget=category_data.default_budget,
        created_by=current_user.id,
        created_by_name=current_user.name,
        created_at=now
    )
    
    session.add(new_category)
    
    await log_audit_pg(
        session, "default_category", category_id, "create", current_user,
        f"إنشاء تصنيف افتراضي: {category_data.name}"
    )
    
    await session.commit()
    
    return {
        "id": category_id,
        "name": category_data.name,
        "default_budget": category_data.default_budget,
        "created_by": current_user.id,
        "created_by_name": current_user.name,
        "created_at": now.isoformat()
    }


@pg_budget_router.put("/default-budget-categories/{category_id}")
async def update_default_budget_category(
    category_id: str,
    update_data: DefaultBudgetCategoryUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a default budget category"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل التصنيفات الافتراضية")
    
    result = await session.execute(
        select(DefaultBudgetCategory).where(DefaultBudgetCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    if update_data.name is not None:
        category.name = update_data.name
    if update_data.default_budget is not None:
        category.default_budget = update_data.default_budget
    
    await session.commit()
    
    return {"message": "تم تحديث التصنيف الافتراضي بنجاح"}


@pg_budget_router.delete("/default-budget-categories/{category_id}")
async def delete_default_budget_category(
    category_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a default budget category"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف التصنيفات الافتراضية")
    
    result = await session.execute(
        select(DefaultBudgetCategory).where(DefaultBudgetCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    await log_audit_pg(
        session, "default_category", category_id, "delete", current_user,
        f"حذف تصنيف افتراضي: {category.name}"
    )
    
    await session.delete(category)
    await session.commit()
    
    return {"message": "تم حذف التصنيف الافتراضي بنجاح"}


# ==================== PROJECT BUDGET CATEGORIES ====================

@pg_budget_router.get("/budget-categories")
async def get_budget_categories(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get budget categories with actual spent amounts"""
    query = select(BudgetCategory)
    if project_id:
        query = query.where(BudgetCategory.project_id == project_id)
    query = query.order_by(desc(BudgetCategory.created_at))
    
    result = await session.execute(query)
    categories = result.scalars().all()
    
    response = []
    for cat in categories:
        # Get actual spent from purchase orders
        spent_result = await session.execute(
            select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
            .select_from(PurchaseOrder)
            .where(PurchaseOrder.category_id == cat.id)
        )
        actual_spent = float(spent_result.scalar() or 0)
        
        remaining = cat.estimated_budget - actual_spent
        variance_percentage = ((actual_spent - cat.estimated_budget) / cat.estimated_budget * 100) if cat.estimated_budget > 0 else 0
        
        response.append({
            "id": cat.id,
            "name": cat.name,
            "project_id": cat.project_id,
            "project_name": cat.project_name,
            "estimated_budget": cat.estimated_budget,
            "actual_spent": actual_spent,
            "remaining": remaining,
            "variance_percentage": round(variance_percentage, 2),
            "created_by": cat.created_by,
            "created_by_name": cat.created_by_name,
            "created_at": cat.created_at.isoformat() if cat.created_at else None
        })
    
    return response


@pg_budget_router.post("/budget-categories")
async def create_budget_category(
    category_data: BudgetCategoryCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a budget category for a project"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه إدارة التصنيفات")
    
    # Get project
    project_result = await session.execute(
        select(Project).where(Project.id == category_data.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    category_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # توليد كود التصنيف تلقائياً إذا لم يُعطى
    category_code = category_data.code
    if not category_code:
        # حساب عدد التصنيفات الحالية لتوليد رقم تسلسلي
        count_result = await session.execute(
            select(func.count()).select_from(BudgetCategory)
        )
        count = count_result.scalar() or 0
        category_code = f"CAT{str(count + 1).zfill(3)}"
    
    new_category = BudgetCategory(
        id=category_id,
        code=category_code,
        name=category_data.name,
        project_id=category_data.project_id,
        project_name=project.name,
        estimated_budget=category_data.estimated_budget,
        created_by=current_user.id,
        created_by_name=current_user.name,
        created_at=now
    )
    
    session.add(new_category)
    
    await log_audit_pg(
        session, "category", category_id, "create", current_user,
        f"إنشاء تصنيف ميزانية: {category_data.name} للمشروع {project.name}"
    )
    
    await session.commit()
    
    return {
        "id": category_id,
        "code": category_code,
        "name": category_data.name,
        "project_id": category_data.project_id,
        "project_name": project.name,
        "estimated_budget": category_data.estimated_budget,
        "created_by": current_user.id,
        "created_by_name": current_user.name,
        "created_at": now.isoformat(),
        "actual_spent": 0,
        "remaining": category_data.estimated_budget,
        "variance_percentage": 0
    }


@pg_budget_router.put("/budget-categories/{category_id}")
async def update_budget_category(
    category_id: str,
    update_data: BudgetCategoryUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a budget category"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تعديل التصنيفات")
    
    result = await session.execute(
        select(BudgetCategory).where(BudgetCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    if update_data.name is not None:
        category.name = update_data.name
    if update_data.estimated_budget is not None:
        category.estimated_budget = update_data.estimated_budget
    
    await session.commit()
    
    return {"message": "تم تحديث التصنيف بنجاح"}


@pg_budget_router.delete("/budget-categories/{category_id}")
async def delete_budget_category(
    category_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a budget category"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه حذف التصنيفات")
    
    # Check if category has orders
    order_result = await session.execute(
        select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.category_id == category_id)
    )
    order_count = order_result.scalar() or 0
    
    if order_count > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف التصنيف لوجود {order_count} أوامر شراء مرتبطة به")
    
    result = await session.execute(
        select(BudgetCategory).where(BudgetCategory.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    
    await log_audit_pg(
        session, "category", category_id, "delete", current_user,
        f"حذف تصنيف ميزانية: {category.name}"
    )
    
    await session.delete(category)
    await session.commit()
    
    return {"message": "تم حذف التصنيف بنجاح"}


@pg_budget_router.post("/default-budget-categories/apply-to-project/{project_id}")
async def apply_default_categories_to_project(
    project_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Apply default categories to an existing project"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه تطبيق التصنيفات")
    
    # Get project
    project_result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get default categories
    default_result = await session.execute(select(DefaultBudgetCategory))
    default_categories = default_result.scalars().all()
    
    if not default_categories:
        raise HTTPException(status_code=400, detail="لا توجد تصنيفات افتراضية")
    
    # Get existing category names for this project
    existing_result = await session.execute(
        select(BudgetCategory.name).where(BudgetCategory.project_id == project_id)
    )
    existing_names = {r[0] for r in existing_result.fetchall()}
    
    now = datetime.utcnow()
    added_count = 0
    
    for default_cat in default_categories:
        if default_cat.name in existing_names:
            continue
        
        category_id = str(uuid.uuid4())
        new_category = BudgetCategory(
            id=category_id,
            name=default_cat.name,
            project_id=project_id,
            project_name=project.name,
            estimated_budget=default_cat.default_budget,
            created_by=current_user.id,
            created_by_name=current_user.name,
            created_at=now
        )
        session.add(new_category)
        added_count += 1
    
    await session.commit()
    
    return {"message": f"تم إضافة {added_count} تصنيف للمشروع", "added_count": added_count}

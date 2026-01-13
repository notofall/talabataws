"""
PostgreSQL Projects Routes - Project Management
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

from database import get_postgres_session, Project, User, BudgetCategory, DefaultBudgetCategory, MaterialRequest, PurchaseOrder, AuditLog

# Create router
pg_projects_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Projects"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class ProjectCreate(BaseModel):
    name: str
    owner_name: str
    description: Optional[str] = None
    location: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    owner_name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    owner_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    status: str
    created_by: str
    created_by_name: str
    created_at: str
    total_requests: int = 0
    total_orders: int = 0
    total_budget: float = 0
    total_spent: float = 0


# ==================== HELPER FUNCTIONS ====================

async def log_audit_pg(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    user: User,
    description: str,
    changes: dict = None
):
    """Log audit event to PostgreSQL"""
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


# ==================== PROJECTS ROUTES ====================

@pg_projects_router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new project - supervisor only"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه إنشاء المشاريع")
    
    project_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    new_project = Project(
        id=project_id,
        name=project_data.name,
        owner_name=project_data.owner_name,
        description=project_data.description,
        location=project_data.location,
        status="active",
        created_by=current_user.id,
        created_by_name=current_user.name,
        created_at=now
    )
    
    session.add(new_project)
    
    # Flush to ensure project is saved before adding budget categories (foreign key constraint)
    await session.flush()
    
    # Copy default budget categories to new project
    result = await session.execute(select(DefaultBudgetCategory))
    default_categories = result.scalars().all()
    
    categories_added = 0
    for default_cat in default_categories:
        category_id = str(uuid.uuid4())
        new_category = BudgetCategory(
            id=category_id,
            name=default_cat.name,
            project_id=project_id,
            project_name=project_data.name,
            estimated_budget=default_cat.default_budget,
            created_by=default_cat.created_by,
            created_by_name=default_cat.created_by_name,
            created_at=now
        )
        session.add(new_category)
        categories_added += 1
    
    # Log audit
    await log_audit_pg(
        session, "project", project_id, "create", current_user,
        f"إنشاء مشروع جديد: {project_data.name} (مع {categories_added} تصنيف)"
    )
    
    await session.commit()
    
    return {
        "id": project_id,
        "name": project_data.name,
        "owner_name": project_data.owner_name,
        "description": project_data.description,
        "location": project_data.location,
        "status": "active",
        "created_by": current_user.id,
        "created_by_name": current_user.name,
        "created_at": now.isoformat(),
        "total_requests": 0,
        "total_orders": 0,
        "total_budget": 0,
        "total_spent": 0,
        "categories_added": categories_added
    }


@pg_projects_router.get("/projects")
async def get_projects(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all projects with stats"""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(desc(Project.created_at))
    
    result = await session.execute(query)
    projects = result.scalars().all()
    
    response = []
    for p in projects:
        # Get request count
        req_result = await session.execute(
            select(func.count()).select_from(MaterialRequest).where(MaterialRequest.project_id == p.id)
        )
        request_count = req_result.scalar() or 0
        
        # Get order count and total spent
        order_result = await session.execute(
            select(
                func.count().label('count'),
                func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label('total')
            ).select_from(PurchaseOrder).where(PurchaseOrder.project_id == p.id)
        )
        order_stats = order_result.first()
        order_count = order_stats.count if order_stats else 0
        total_spent = float(order_stats.total) if order_stats else 0
        
        # Get total budget from categories
        budget_result = await session.execute(
            select(func.coalesce(func.sum(BudgetCategory.estimated_budget), 0))
            .select_from(BudgetCategory).where(BudgetCategory.project_id == p.id)
        )
        total_budget = float(budget_result.scalar() or 0)
        
        response.append({
            "id": p.id,
            "name": p.name,
            "owner_name": p.owner_name,
            "description": p.description,
            "location": p.location,
            "status": p.status,
            "created_by": p.created_by,
            "created_by_name": p.created_by_name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "total_requests": request_count,
            "total_orders": order_count,
            "total_budget": total_budget,
            "total_spent": total_spent
        })
    
    return response


@pg_projects_router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single project by ID"""
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get stats
    req_result = await session.execute(
        select(func.count()).select_from(MaterialRequest).where(MaterialRequest.project_id == project_id)
    )
    request_count = req_result.scalar() or 0
    
    order_result = await session.execute(
        select(
            func.count().label('count'),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label('total')
        ).select_from(PurchaseOrder).where(PurchaseOrder.project_id == project_id)
    )
    order_stats = order_result.first()
    
    budget_result = await session.execute(
        select(func.coalesce(func.sum(BudgetCategory.estimated_budget), 0))
        .select_from(BudgetCategory).where(BudgetCategory.project_id == project_id)
    )
    
    return {
        "id": project.id,
        "name": project.name,
        "owner_name": project.owner_name,
        "description": project.description,
        "location": project.location,
        "status": project.status,
        "created_by": project.created_by,
        "created_by_name": project.created_by_name,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "total_requests": request_count,
        "total_orders": order_stats.count if order_stats else 0,
        "total_budget": float(budget_result.scalar() or 0),
        "total_spent": float(order_stats.total) if order_stats else 0
    }


@pg_projects_router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Update a project - supervisor only"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه تعديل المشاريع")
    
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    changes = {}
    
    if update_data.name is not None and project.name != update_data.name:
        changes["name"] = {"old": project.name, "new": update_data.name}
        project.name = update_data.name
    
    if update_data.owner_name is not None and project.owner_name != update_data.owner_name:
        changes["owner_name"] = {"old": project.owner_name, "new": update_data.owner_name}
        project.owner_name = update_data.owner_name
    
    if update_data.description is not None and project.description != update_data.description:
        changes["description"] = {"old": project.description, "new": update_data.description}
        project.description = update_data.description
    
    if update_data.location is not None and project.location != update_data.location:
        changes["location"] = {"old": project.location, "new": update_data.location}
        project.location = update_data.location
    
    if update_data.status is not None and project.status != update_data.status:
        changes["status"] = {"old": project.status, "new": update_data.status}
        project.status = update_data.status
    
    if changes:
        await log_audit_pg(
            session, "project", project_id, "update", current_user,
            f"تحديث المشروع: {project.name}", changes
        )
        await session.commit()
    
    return {"message": "تم تحديث المشروع بنجاح"}


@pg_projects_router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Delete a project - supervisor only"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه حذف المشاريع")
    
    # Check if project has requests
    req_result = await session.execute(
        select(func.count()).select_from(MaterialRequest).where(MaterialRequest.project_id == project_id)
    )
    request_count = req_result.scalar() or 0
    
    if request_count > 0:
        raise HTTPException(status_code=400, detail=f"لا يمكن حذف المشروع لوجود {request_count} طلبات مرتبطة به")
    
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    project_name = project.name
    
    # Delete related budget categories first
    await session.execute(
        BudgetCategory.__table__.delete().where(BudgetCategory.project_id == project_id)
    )
    
    await session.delete(project)
    
    await log_audit_pg(
        session, "project", project_id, "delete", current_user,
        f"حذف المشروع: {project_name}"
    )
    
    await session.commit()
    
    return {"message": "تم حذف المشروع بنجاح"}

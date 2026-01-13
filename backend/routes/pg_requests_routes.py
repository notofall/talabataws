"""
PostgreSQL Material Requests Routes
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
    get_postgres_session, MaterialRequest, MaterialRequestItem,
    User, Project, AuditLog
)

# Create router
pg_requests_router = APIRouter(prefix="/api/pg", tags=["PostgreSQL Material Requests"])

# Import auth dependency
from routes.pg_auth_routes import get_current_user_pg, UserRole


# ==================== PYDANTIC MODELS ====================

class MaterialItemCreate(BaseModel):
    name: str
    quantity: int
    unit: str = "قطعة"
    estimated_price: Optional[float] = None


class MaterialRequestCreate(BaseModel):
    items: List[MaterialItemCreate]
    project_id: str
    reason: str
    engineer_id: str
    expected_delivery_date: Optional[str] = None


class MaterialRequestUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


class RejectRequestData(BaseModel):
    reason: str


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


async def get_next_request_number(session: AsyncSession, supervisor_id: str) -> tuple:
    """Get next sequential request number for a supervisor"""
    # Get supervisor
    result = await session.execute(select(User).where(User.id == supervisor_id))
    supervisor = result.scalar_one_or_none()
    
    if not supervisor:
        return "X1", 1
    
    prefix = supervisor.supervisor_prefix or "X"
    
    # Find highest request sequence for this supervisor
    result = await session.execute(
        select(func.max(MaterialRequest.request_seq))
        .where(MaterialRequest.supervisor_id == supervisor_id)
    )
    max_seq = result.scalar() or 0
    next_seq = max_seq + 1
    
    return f"{prefix}{next_seq}", next_seq


# ==================== MATERIAL REQUESTS ROUTES ====================

@pg_requests_router.post("/requests")
async def create_material_request(
    request_data: MaterialRequestCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new material request - supervisor only"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="فقط المشرف يمكنه إنشاء طلبات المواد")
    
    # Get project
    project_result = await session.execute(
        select(Project).where(Project.id == request_data.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود")
    
    # Get engineer
    engineer_result = await session.execute(
        select(User).where(User.id == request_data.engineer_id)
    )
    engineer = engineer_result.scalar_one_or_none()
    
    if not engineer:
        raise HTTPException(status_code=404, detail="المهندس غير موجود")
    
    request_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get request number
    request_number, request_seq = await get_next_request_number(session, current_user.id)
    
    # Create request
    new_request = MaterialRequest(
        id=request_id,
        request_number=request_number,
        request_seq=request_seq,
        project_id=project.id,
        project_name=project.name,
        reason=request_data.reason,
        supervisor_id=current_user.id,
        supervisor_name=current_user.name,
        engineer_id=engineer.id,
        engineer_name=engineer.name,
        status="pending_engineer",
        expected_delivery_date=request_data.expected_delivery_date,
        created_at=now
    )
    session.add(new_request)
    
    # Create items
    items_response = []
    for idx, item in enumerate(request_data.items):
        item_id = str(uuid.uuid4())
        new_item = MaterialRequestItem(
            id=item_id,
            request_id=request_id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            estimated_price=item.estimated_price,
            item_index=idx
        )
        session.add(new_item)
        items_response.append({
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
            "estimated_price": item.estimated_price
        })
    
    await log_audit_pg(
        session, "request", request_id, "create", current_user,
        f"إنشاء طلب مواد جديد: {request_number}"
    )
    
    await session.commit()
    
    return {
        "id": request_id,
        "request_number": request_number,
        "request_seq": request_seq,
        "items": items_response,
        "project_id": project.id,
        "project_name": project.name,
        "reason": request_data.reason,
        "supervisor_id": current_user.id,
        "supervisor_name": current_user.name,
        "engineer_id": engineer.id,
        "engineer_name": engineer.name,
        "status": "pending_engineer",
        "expected_delivery_date": request_data.expected_delivery_date,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }


@pg_requests_router.get("/requests")
async def get_material_requests(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get material requests based on user role"""
    query = select(MaterialRequest)
    
    # Filter based on role
    if current_user.role == UserRole.SUPERVISOR:
        query = query.where(MaterialRequest.supervisor_id == current_user.id)
    elif current_user.role == UserRole.ENGINEER:
        query = query.where(MaterialRequest.engineer_id == current_user.id)
    
    if status:
        query = query.where(MaterialRequest.status == status)
    if project_id:
        query = query.where(MaterialRequest.project_id == project_id)
    
    query = query.order_by(desc(MaterialRequest.created_at))
    
    result = await session.execute(query)
    requests = result.scalars().all()
    
    response = []
    for req in requests:
        # Get items
        items_result = await session.execute(
            select(MaterialRequestItem)
            .where(MaterialRequestItem.request_id == req.id)
            .order_by(MaterialRequestItem.item_index)
        )
        items = items_result.scalars().all()
        
        response.append({
            "id": req.id,
            "request_number": req.request_number,
            "request_seq": req.request_seq,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "estimated_price": item.estimated_price
                }
                for item in items
            ],
            "project_id": req.project_id,
            "project_name": req.project_name,
            "reason": req.reason,
            "supervisor_id": req.supervisor_id,
            "supervisor_name": req.supervisor_name,
            "engineer_id": req.engineer_id,
            "engineer_name": req.engineer_name,
            "status": req.status,
            "rejection_reason": req.rejection_reason,
            "expected_delivery_date": req.expected_delivery_date,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None
        })
    
    return response


@pg_requests_router.get("/requests/{request_id}")
async def get_material_request(
    request_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get a single material request"""
    result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    # Get items
    items_result = await session.execute(
        select(MaterialRequestItem)
        .where(MaterialRequestItem.request_id == request_id)
        .order_by(MaterialRequestItem.item_index)
    )
    items = items_result.scalars().all()
    
    return {
        "id": req.id,
        "request_number": req.request_number,
        "request_seq": req.request_seq,
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "estimated_price": item.estimated_price
            }
            for item in items
        ],
        "project_id": req.project_id,
        "project_name": req.project_name,
        "reason": req.reason,
        "supervisor_id": req.supervisor_id,
        "supervisor_name": req.supervisor_name,
        "engineer_id": req.engineer_id,
        "engineer_name": req.engineer_name,
        "status": req.status,
        "rejection_reason": req.rejection_reason,
        "expected_delivery_date": req.expected_delivery_date,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "updated_at": req.updated_at.isoformat() if req.updated_at else None
    }


@pg_requests_router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Approve a material request - engineer only"""
    if current_user.role != UserRole.ENGINEER:
        raise HTTPException(status_code=403, detail="فقط المهندس يمكنه اعتماد الطلبات")
    
    result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if req.status != "pending_engineer":
        raise HTTPException(status_code=400, detail="لا يمكن اعتماد هذا الطلب")
    
    if req.engineer_id != current_user.id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير موجه إليك")
    
    req.status = "approved_by_engineer"
    req.updated_at = datetime.utcnow()
    
    await log_audit_pg(
        session, "request", request_id, "approve", current_user,
        f"اعتماد طلب المواد: {req.request_number}"
    )
    
    await session.commit()
    
    return {"message": "تم اعتماد الطلب بنجاح", "status": "approved_by_engineer"}


@pg_requests_router.post("/requests/{request_id}/reject")
async def reject_request(
    request_id: str,
    rejection_data: MaterialRequestUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Reject a material request - engineer only"""
    if current_user.role != UserRole.ENGINEER:
        raise HTTPException(status_code=403, detail="فقط المهندس يمكنه رفض الطلبات")
    
    result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if req.status != "pending_engineer":
        raise HTTPException(status_code=400, detail="لا يمكن رفض هذا الطلب")
    
    if req.engineer_id != current_user.id:
        raise HTTPException(status_code=403, detail="هذا الطلب غير موجه إليك")
    
    req.status = "rejected_by_engineer"
    req.rejection_reason = rejection_data.rejection_reason
    req.updated_at = datetime.utcnow()
    
    await log_audit_pg(
        session, "request", request_id, "reject", current_user,
        f"رفض طلب المواد: {req.request_number}"
    )
    
    await session.commit()
    
    return {"message": "تم رفض الطلب", "status": "rejected_by_engineer"}


@pg_requests_router.post("/requests/{request_id}/reject-manager")
async def reject_request_by_manager(
    request_id: str,
    rejection_data: MaterialRequestUpdate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Reject a request by procurement manager - sends back to engineer"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="فقط مدير المشتريات يمكنه رفض الطلبات")
    
    result = await session.execute(
        select(MaterialRequest).where(MaterialRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if req.status != "approved_by_engineer":
        raise HTTPException(status_code=400, detail="لا يمكن رفض هذا الطلب")
    
    req.status = "rejected_by_manager"
    req.rejection_reason = rejection_data.rejection_reason
    req.updated_at = datetime.utcnow()
    
    await log_audit_pg(
        session, "request", request_id, "reject_manager", current_user,
        f"رفض طلب المواد من مدير المشتريات: {req.request_number}"
    )
    
    await session.commit()
    
    return {"message": "تم رفض الطلب وإعادته للمهندس", "status": "rejected_by_manager"}


@pg_requests_router.get("/requests/approved")
async def get_approved_requests(
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get all approved requests - for procurement manager"""
    if current_user.role != UserRole.PROCUREMENT_MANAGER:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
    result = await session.execute(
        select(MaterialRequest)
        .where(MaterialRequest.status.in_(["approved_by_engineer", "partially_ordered"]))
        .order_by(desc(MaterialRequest.created_at))
    )
    requests = result.scalars().all()
    
    response = []
    for req in requests:
        items_result = await session.execute(
            select(MaterialRequestItem)
            .where(MaterialRequestItem.request_id == req.id)
            .order_by(MaterialRequestItem.item_index)
        )
        items = items_result.scalars().all()
        
        response.append({
            "id": req.id,
            "request_number": req.request_number,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "estimated_price": item.estimated_price
                }
                for item in items
            ],
            "project_id": req.project_id,
            "project_name": req.project_name,
            "reason": req.reason,
            "supervisor_name": req.supervisor_name,
            "engineer_name": req.engineer_name,
            "status": req.status,
            "created_at": req.created_at.isoformat() if req.created_at else None
        })
    
    return response

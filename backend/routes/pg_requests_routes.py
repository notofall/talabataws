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
from sqlalchemy import desc
import uuid
import json

from database import (
    get_postgres_session, MaterialRequest, MaterialRequestItem,
    User, AuditLog
)
from app.requests.application.use_cases import (
    CreateMaterialRequestCommand,
    CreateMaterialRequestUseCase,
    ListMaterialRequestsQuery,
    ListMaterialRequestsUseCase,
    MaterialItemInput,
)
from app.requests.domain.errors import InvalidRequest, NotFound, PermissionDenied
from app.requests.domain.models import UserSummary
from app.requests.infrastructure.sqlalchemy_repository import (
    SqlAlchemyMaterialRequestRepository,
)
from app.requests.presentation.response_mapper import material_request_to_response

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


def to_user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=user.id,
        name=user.name,
        role=user.role,
        supervisor_prefix=user.supervisor_prefix,
    )


# ==================== MATERIAL REQUESTS ROUTES ====================

@pg_requests_router.post("/requests")
async def create_material_request(
    request_data: MaterialRequestCreate,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Create a new material request - supervisor only"""
    repository = SqlAlchemyMaterialRequestRepository(session)
    use_case = CreateMaterialRequestUseCase(
        repository=repository,
        id_generator=lambda: str(uuid.uuid4()),
        clock=datetime.utcnow,
    )
    command = CreateMaterialRequestCommand(
        items=[
            MaterialItemInput(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                estimated_price=item.estimated_price,
            )
            for item in request_data.items
        ],
        project_id=request_data.project_id,
        reason=request_data.reason,
        engineer_id=request_data.engineer_id,
        expected_delivery_date=request_data.expected_delivery_date,
    )

    try:
        request = await use_case.execute(command, to_user_summary(current_user))
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=exc.message)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=exc.message)
    except InvalidRequest as exc:
        raise HTTPException(status_code=400, detail=exc.message)

    return material_request_to_response(request)


@pg_requests_router.get("/requests")
async def get_material_requests(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user_pg),
    session: AsyncSession = Depends(get_postgres_session)
):
    """Get material requests based on user role"""
    allowed_roles = {
        UserRole.SUPERVISOR,
        UserRole.ENGINEER,
        UserRole.PROCUREMENT_MANAGER,
        UserRole.GENERAL_MANAGER,
        UserRole.SYSTEM_ADMIN,
    }
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")

    repository = SqlAlchemyMaterialRequestRepository(session)
    use_case = ListMaterialRequestsUseCase(repository)
    query = ListMaterialRequestsQuery(
        status=status,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    requests = await use_case.execute(query, to_user_summary(current_user))

    return [material_request_to_response(req) for req in requests]


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

    if current_user.role == UserRole.SUPERVISOR and req.supervisor_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الطلب")
    if current_user.role == UserRole.ENGINEER and req.engineer_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الطلب")
    if current_user.role not in [
        UserRole.SUPERVISOR,
        UserRole.ENGINEER,
        UserRole.PROCUREMENT_MANAGER,
        UserRole.GENERAL_MANAGER,
        UserRole.SYSTEM_ADMIN,
    ]:
        raise HTTPException(status_code=403, detail="غير مصرح لك بهذا الإجراء")
    
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
    rejection_data: RejectRequestData,
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
    req.rejection_reason = rejection_data.reason
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
    rejection_data: RejectRequestData,
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
    req.rejection_reason = rejection_data.reason
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

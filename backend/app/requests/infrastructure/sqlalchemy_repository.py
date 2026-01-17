import uuid
from typing import Optional, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.requests.application.ports import MaterialRequestRepository
from app.requests.domain.models import (
    AuditEntry,
    MaterialRequest,
    MaterialRequestItem,
    ProjectSummary,
    RequestFilters,
    UserSummary,
)
from database import (
    AuditLog,
    MaterialRequest as MaterialRequestModel,
    MaterialRequestItem as MaterialRequestItemModel,
    Project,
    User,
)


class SqlAlchemyMaterialRequestRepository(MaterialRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project(self, project_id: str) -> Optional[ProjectSummary]:
        result = await self._session.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            return None
        return ProjectSummary(id=project.id, name=project.name)

    async def get_user(self, user_id: str) -> Optional[UserSummary]:
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        return UserSummary(
            id=user.id,
            name=user.name,
            role=user.role,
            supervisor_prefix=user.supervisor_prefix,
        )

    async def get_next_request_number(self, supervisor_id: str) -> tuple[str, int]:
        result = await self._session.execute(
            select(User.supervisor_prefix).where(User.id == supervisor_id)
        )
        supervisor_prefix = result.scalar_one_or_none()
        prefix = supervisor_prefix or "X"

        result = await self._session.execute(
            select(func.max(MaterialRequestModel.request_seq)).where(
                MaterialRequestModel.supervisor_id == supervisor_id
            )
        )
        max_seq = result.scalar() or 0
        next_seq = max_seq + 1
        return f"{prefix}{next_seq}", next_seq

    async def add_request(self, request: MaterialRequest) -> None:
        new_request = MaterialRequestModel(
            id=request.id,
            request_number=request.request_number,
            request_seq=request.request_seq,
            project_id=request.project_id,
            project_name=request.project_name,
            reason=request.reason,
            supervisor_id=request.supervisor_id,
            supervisor_name=request.supervisor_name,
            engineer_id=request.engineer_id,
            engineer_name=request.engineer_name,
            status=request.status,
            expected_delivery_date=request.expected_delivery_date,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        self._session.add(new_request)

        for item in request.items:
            new_item = MaterialRequestItemModel(
                id=str(uuid.uuid4()),
                request_id=request.id,
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                estimated_price=item.estimated_price,
                item_index=item.item_index,
            )
            self._session.add(new_item)

    async def add_audit_entry(self, entry: AuditEntry) -> None:
        audit_log = AuditLog(
            id=entry.id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            action=entry.action,
            changes=entry.changes,
            user_id=entry.user_id,
            user_name=entry.user_name,
            user_role=entry.user_role,
            description=entry.description,
            timestamp=entry.timestamp,
        )
        self._session.add(audit_log)

    async def list_requests(self, filters: RequestFilters) -> Sequence[MaterialRequest]:
        query = select(MaterialRequestModel)

        if filters.supervisor_id:
            query = query.where(MaterialRequestModel.supervisor_id == filters.supervisor_id)
        if filters.engineer_id:
            query = query.where(MaterialRequestModel.engineer_id == filters.engineer_id)
        if filters.status:
            query = query.where(MaterialRequestModel.status == filters.status)
        if filters.project_id:
            query = query.where(MaterialRequestModel.project_id == filters.project_id)

        query = query.order_by(desc(MaterialRequestModel.created_at))
        query = query.limit(filters.limit).offset(filters.offset)

        result = await self._session.execute(query)
        requests = result.scalars().all()

        items_by_request: dict[str, list[MaterialRequestItem]] = {}
        request_ids = [req.id for req in requests]
        if request_ids:
            items_result = await self._session.execute(
                select(MaterialRequestItemModel)
                .where(MaterialRequestItemModel.request_id.in_(request_ids))
                .order_by(
                    MaterialRequestItemModel.request_id,
                    MaterialRequestItemModel.item_index,
                )
            )
            for item in items_result.scalars().all():
                items_by_request.setdefault(item.request_id, []).append(
                    MaterialRequestItem(
                        name=item.name,
                        quantity=item.quantity,
                        unit=item.unit,
                        estimated_price=item.estimated_price,
                        item_index=item.item_index,
                    )
                )

        return [
            MaterialRequest(
                id=req.id,
                request_number=req.request_number,
                request_seq=req.request_seq,
                project_id=req.project_id,
                project_name=req.project_name,
                reason=req.reason,
                supervisor_id=req.supervisor_id,
                supervisor_name=req.supervisor_name,
                engineer_id=req.engineer_id,
                engineer_name=req.engineer_name,
                status=req.status,
                rejection_reason=req.rejection_reason,
                expected_delivery_date=req.expected_delivery_date,
                created_at=req.created_at,
                updated_at=req.updated_at,
                items=items_by_request.get(req.id, []),
            )
            for req in requests
        ]

    async def commit(self) -> None:
        await self._session.commit()

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Sequence

from app.requests.application.ports import MaterialRequestRepository
from app.requests.domain.errors import InvalidRequest, NotFound, PermissionDenied
from app.requests.domain.models import (
    AuditEntry,
    MaterialRequest,
    MaterialRequestItem,
    RequestFilters,
    UserSummary,
)


@dataclass(frozen=True)
class MaterialItemInput:
    name: str
    quantity: int
    unit: str
    estimated_price: Optional[float] = None


@dataclass(frozen=True)
class CreateMaterialRequestCommand:
    items: Sequence[MaterialItemInput]
    project_id: str
    reason: str
    engineer_id: str
    expected_delivery_date: Optional[str] = None


@dataclass(frozen=True)
class ListMaterialRequestsQuery:
    status: Optional[str] = None
    project_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


IdGenerator = Callable[[], str]
Clock = Callable[[], datetime]


class CreateMaterialRequestUseCase:
    def __init__(
        self,
        repository: MaterialRequestRepository,
        id_generator: IdGenerator,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator
        self._clock = clock

    async def execute(
        self,
        command: CreateMaterialRequestCommand,
        current_user: UserSummary,
    ) -> MaterialRequest:
        if current_user.role != "supervisor":
            raise PermissionDenied("فقط المشرف يمكنه إنشاء طلبات المواد")

        if not command.items:
            raise InvalidRequest("يجب إضافة صنف واحد على الأقل")

        for item in command.items:
            if not item.name.strip():
                raise InvalidRequest("اسم الصنف مطلوب")
            if item.quantity <= 0:
                raise InvalidRequest("الكمية يجب أن تكون أكبر من صفر")

        project = await self._repository.get_project(command.project_id)
        if project is None:
            raise NotFound("المشروع غير موجود")

        engineer = await self._repository.get_user(command.engineer_id)
        if engineer is None:
            raise NotFound("المهندس غير موجود")

        request_number, request_seq = await self._repository.get_next_request_number(
            current_user.id
        )
        now = self._clock()
        request_id = self._id_generator()

        items = [
            MaterialRequestItem(
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                estimated_price=item.estimated_price,
                item_index=index,
            )
            for index, item in enumerate(command.items)
        ]

        request = MaterialRequest(
            id=request_id,
            request_number=request_number,
            request_seq=request_seq,
            project_id=project.id,
            project_name=project.name,
            reason=command.reason,
            supervisor_id=current_user.id,
            supervisor_name=current_user.name,
            engineer_id=engineer.id,
            engineer_name=engineer.name,
            status="pending_engineer",
            expected_delivery_date=command.expected_delivery_date,
            created_at=now,
            updated_at=now,
            items=items,
        )

        await self._repository.add_request(request)

        audit_entry = AuditEntry(
            id=self._id_generator(),
            entity_type="request",
            entity_id=request_id,
            action="create",
            user_id=current_user.id,
            user_name=current_user.name,
            user_role=current_user.role,
            description=f"إنشاء طلب مواد جديد: {request_number}",
            timestamp=now,
            changes=None,
        )
        await self._repository.add_audit_entry(audit_entry)
        await self._repository.commit()

        return request


class ListMaterialRequestsUseCase:
    def __init__(
        self,
        repository: MaterialRequestRepository,
        max_limit: int = 200,
    ) -> None:
        self._repository = repository
        self._max_limit = max_limit

    async def execute(
        self,
        query: ListMaterialRequestsQuery,
        current_user: UserSummary,
    ) -> Sequence[MaterialRequest]:
        limit = max(1, min(query.limit, self._max_limit))
        offset = max(0, query.offset)
        filters = RequestFilters(
            status=query.status,
            project_id=query.project_id,
            limit=limit,
            offset=offset,
        )

        if current_user.role == "supervisor":
            filters = RequestFilters(
                supervisor_id=current_user.id,
                status=filters.status,
                project_id=filters.project_id,
                limit=filters.limit,
                offset=filters.offset,
            )
        elif current_user.role == "engineer":
            filters = RequestFilters(
                engineer_id=current_user.id,
                status=filters.status,
                project_id=filters.project_id,
                limit=filters.limit,
                offset=filters.offset,
            )

        return await self._repository.list_requests(filters)

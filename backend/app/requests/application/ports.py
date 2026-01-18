from typing import Optional, Protocol, Sequence

from app.requests.domain.models import (
    AuditEntry,
    MaterialRequest,
    ProjectSummary,
    RequestFilters,
    UserSummary,
)


class MaterialRequestRepository(Protocol):
    async def get_project(self, project_id: str) -> Optional[ProjectSummary]:
        ...

    async def get_user(self, user_id: str) -> Optional[UserSummary]:
        ...

    async def get_next_request_number(self, supervisor_id: str) -> tuple[str, int]:
        ...

    async def add_request(self, request: MaterialRequest) -> None:
        ...

    async def add_audit_entry(self, entry: AuditEntry) -> None:
        ...

    async def list_requests(self, filters: RequestFilters) -> Sequence[MaterialRequest]:
        ...

    async def commit(self) -> None:
        ...

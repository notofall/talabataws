import asyncio
from datetime import datetime

import pytest

from app.requests.application.use_cases import (
    CreateMaterialRequestCommand,
    CreateMaterialRequestUseCase,
    ListMaterialRequestsQuery,
    ListMaterialRequestsUseCase,
    MaterialItemInput,
)
from app.requests.domain.errors import NotFound, PermissionDenied
from app.requests.domain.models import ProjectSummary, UserSummary


class FakeMaterialRequestRepository:
    def __init__(self) -> None:
        self.projects = {}
        self.users = {}
        self.requests = []
        self.audit_entries = []
        self.committed = False
        self.next_request_number = ("A1", 1)
        self.list_requests_result = []
        self.last_filters = None

    async def get_project(self, project_id: str):
        return self.projects.get(project_id)

    async def get_user(self, user_id: str):
        return self.users.get(user_id)

    async def get_next_request_number(self, supervisor_id: str):
        return self.next_request_number

    async def add_request(self, request):
        self.requests.append(request)

    async def add_audit_entry(self, entry):
        self.audit_entries.append(entry)

    async def list_requests(self, filters):
        self.last_filters = filters
        return list(self.list_requests_result)

    async def commit(self):
        self.committed = True


def run(coro):
    return asyncio.run(coro)


def test_create_request_denies_non_supervisor():
    repo = FakeMaterialRequestRepository()
    use_case = CreateMaterialRequestUseCase(
        repository=repo,
        id_generator=lambda: "id-1",
        clock=lambda: datetime(2026, 1, 17, 10, 0, 0),
    )
    command = CreateMaterialRequestCommand(
        items=[MaterialItemInput(name="item", quantity=1, unit="قطعة")],
        project_id="project-1",
        reason="reason",
        engineer_id="engineer-1",
    )
    current_user = UserSummary(id="u-1", name="User", role="engineer")

    with pytest.raises(PermissionDenied):
        run(use_case.execute(command, current_user))


def test_create_request_missing_project():
    repo = FakeMaterialRequestRepository()
    repo.users["engineer-1"] = UserSummary(id="engineer-1", name="Eng", role="engineer")
    use_case = CreateMaterialRequestUseCase(
        repository=repo,
        id_generator=lambda: "id-1",
        clock=lambda: datetime(2026, 1, 17, 10, 0, 0),
    )
    command = CreateMaterialRequestCommand(
        items=[MaterialItemInput(name="item", quantity=1, unit="قطعة")],
        project_id="project-1",
        reason="reason",
        engineer_id="engineer-1",
    )
    current_user = UserSummary(id="super-1", name="Sup", role="supervisor")

    with pytest.raises(NotFound):
        run(use_case.execute(command, current_user))


def test_create_request_persists_and_logs():
    repo = FakeMaterialRequestRepository()
    repo.projects["project-1"] = ProjectSummary(id="project-1", name="Project")
    repo.users["engineer-1"] = UserSummary(id="engineer-1", name="Eng", role="engineer")
    ids = iter(["request-1", "audit-1"])
    use_case = CreateMaterialRequestUseCase(
        repository=repo,
        id_generator=lambda: next(ids),
        clock=lambda: datetime(2026, 1, 17, 10, 0, 0),
    )
    command = CreateMaterialRequestCommand(
        items=[
            MaterialItemInput(name="item-a", quantity=2, unit="قطعة"),
            MaterialItemInput(name="item-b", quantity=3, unit="متر", estimated_price=10.0),
        ],
        project_id="project-1",
        reason="reason",
        engineer_id="engineer-1",
        expected_delivery_date="2026-02-01",
    )
    current_user = UserSummary(id="super-1", name="Sup", role="supervisor")

    request = run(use_case.execute(command, current_user))

    assert repo.committed is True
    assert len(repo.requests) == 1
    assert len(repo.audit_entries) == 1
    assert request.request_number == "A1"
    assert request.status == "pending_engineer"
    assert request.items[0].item_index == 0
    assert request.items[1].item_index == 1


def test_list_requests_applies_role_filters():
    repo = FakeMaterialRequestRepository()
    use_case = ListMaterialRequestsUseCase(repository=repo)
    query = ListMaterialRequestsQuery(status="pending_engineer", limit=10, offset=0)
    supervisor = UserSummary(id="super-1", name="Sup", role="supervisor")
    engineer = UserSummary(id="eng-1", name="Eng", role="engineer")

    run(use_case.execute(query, supervisor))
    assert repo.last_filters.supervisor_id == "super-1"
    assert repo.last_filters.engineer_id is None

    run(use_case.execute(query, engineer))
    assert repo.last_filters.engineer_id == "eng-1"


def test_list_requests_clamps_limit_offset():
    repo = FakeMaterialRequestRepository()
    use_case = ListMaterialRequestsUseCase(repository=repo, max_limit=200)
    query = ListMaterialRequestsQuery(status=None, project_id=None, limit=999, offset=-5)
    user = UserSummary(id="u-1", name="User", role="system_admin")

    run(use_case.execute(query, user))

    assert repo.last_filters.limit == 200
    assert repo.last_filters.offset == 0

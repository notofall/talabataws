from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Sequence


@dataclass(frozen=True)
class UserSummary:
    id: str
    name: str
    role: str
    supervisor_prefix: Optional[str] = None


@dataclass(frozen=True)
class ProjectSummary:
    id: str
    name: str


@dataclass(frozen=True)
class MaterialRequestItem:
    name: str
    quantity: int
    unit: str
    estimated_price: Optional[float]
    item_index: int


@dataclass(frozen=True)
class MaterialRequest:
    id: str
    request_number: Optional[str]
    request_seq: Optional[int]
    project_id: str
    project_name: str
    reason: str
    supervisor_id: str
    supervisor_name: str
    engineer_id: str
    engineer_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    expected_delivery_date: Optional[str] = None
    rejection_reason: Optional[str] = None
    items: Sequence[MaterialRequestItem] = field(default_factory=list)


@dataclass(frozen=True)
class AuditEntry:
    id: str
    entity_type: str
    entity_id: str
    action: str
    user_id: str
    user_name: str
    user_role: str
    description: str
    timestamp: datetime
    changes: Optional[str] = None


@dataclass(frozen=True)
class RequestFilters:
    supervisor_id: Optional[str] = None
    engineer_id: Optional[str] = None
    status: Optional[str] = None
    project_id: Optional[str] = None
    limit: int = 50
    offset: int = 0

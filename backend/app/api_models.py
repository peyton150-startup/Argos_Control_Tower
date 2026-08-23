from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class HealthResponse(APIModel):
    status: Literal["ready"]
    factory_as_of: datetime
    source_sha256: str


class DataHealthResponse(APIModel):
    raw_rows: int
    trusted_rows: int
    duplicate_event_ids: int
    exact_duplicate_copies: int
    conflicting_duplicate_ids: int
    quarantined_event_ids: list[str]
    validation_issue_count: int
    reconciliation_issues: list[str]


class FactoryOverviewResponse(APIModel):
    jobs_created: int
    completed_jobs: int
    open_jobs: int
    overdue_open_jobs: int
    blocked_jobs: int
    late_completed_jobs: int
    completed_quantity: int
    good_quantity: int
    scrap_quantity: int
    aggregate_yield: Decimal | None
    known_priced_work_at_risk: Decimal
    priced_overdue_open_jobs: int
    overdue_open_jobs_for_pricing: int


class OverviewResponse(APIModel):
    factory_as_of: datetime
    data_health: DataHealthResponse
    overview: FactoryOverviewResponse


class AttentionResponse(APIModel):
    id: str
    severity: str
    category: Literal["BLOCKED_AND_OVERDUE", "BLOCKED", "OVERDUE"]
    title: str
    entity_type: str
    entity_id: str
    why_it_matters: str
    supporting_facts: dict[str, str]
    evidence_event_ids: list[str]


class JobSummaryResponse(APIModel):
    job_id: str
    customer_id: str | None
    part_id: str | None
    material: str | None
    priority: str | None
    facility: str | None
    tool_id: str | None
    target_due_at: datetime | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    is_blocked: bool
    block_reason: str | None
    is_overdue: bool
    completed_late: bool
    estimated_value: Decimal | None


class EventResponse(APIModel):
    event_id: str
    timestamp: datetime
    event_type: str
    job_id: str | None
    part_id: str | None
    customer_id: str | None
    machine_id: str | None
    material: str | None
    quantity: int | None
    metadata: dict[str, str | int | float | bool | None]


class JobDetailResponse(JobSummaryResponse):
    target_quantity: int | None
    blocked_at: datetime | None
    unit_price_estimate: Decimal | None
    completed_quantity: int | None
    good_quantity: int | None
    scrap_quantity: int | None
    yield_rate: Decimal | None
    created_event_id: str
    block_event_id: str | None
    completion_event_id: str | None
    timeline: list[EventResponse]


class QualityResponse(APIModel):
    inspection_passed_events: int
    inspection_failed_events: int
    inspection_event_pass_rate: Decimal | None
    defect_counts: dict[str, int]

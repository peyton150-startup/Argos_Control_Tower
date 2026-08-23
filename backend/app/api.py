from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.api_models import (
    AttentionResponse,
    DataHealthResponse,
    EventResponse,
    FactoryOverviewResponse,
    HealthResponse,
    JobDetailResponse,
    JobSummaryResponse,
    OverviewResponse,
    QualityResponse,
)
from app.domain import AttentionItem, FactoryState, JobState, NormalizedEvent
from app.ingest import load_events
from app.projection import project_factory_state

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA_PATH = _BACKEND_ROOT / "data" / "manufacturing_events.jsonl"
_api_key_header = APIKeyHeader(name="X-Internal-Key", auto_error=False)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    data_path: Path
    internal_api_key: str

    def __post_init__(self) -> None:
        if not self.internal_api_key.strip():
            raise RuntimeError("INTERNAL_API_KEY must be set to a nonblank value")


def load_runtime_config() -> RuntimeConfig:
    internal_api_key = os.environ.get("INTERNAL_API_KEY", "")
    data_path_override = os.environ.get("DATA_PATH")
    if data_path_override is None:
        data_path = _DEFAULT_DATA_PATH
    else:
        if not data_path_override.strip():
            raise RuntimeError("DATA_PATH must be set to a nonblank value when provided")
        data_path = Path(data_path_override)
        if not data_path.is_absolute():
            data_path = _BACKEND_ROOT / data_path
    return RuntimeConfig(data_path=data_path, internal_api_key=internal_api_key)


def get_factory_state(request: Request) -> FactoryState:
    return request.app.state.factory_state


FactoryStateDependency = Annotated[FactoryState, Depends(get_factory_state)]


async def require_internal_key(
    request: Request,
    provided_key: str | None = Security(_api_key_header),
) -> None:
    expected_key = request.app.state.internal_api_key
    if provided_key is None or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "APIKey"},
        )


def _data_health_response(state: FactoryState) -> DataHealthResponse:
    health = state.data_health
    return DataHealthResponse(
        raw_rows=health.raw_rows,
        trusted_rows=health.trusted_rows,
        duplicate_event_ids=health.duplicate_event_ids,
        exact_duplicate_copies=health.exact_duplicate_copies,
        conflicting_duplicate_ids=health.conflicting_duplicate_ids,
        quarantined_event_ids=list(health.quarantined_event_ids),
        validation_issue_count=health.validation_issue_count,
        reconciliation_issues=list(health.reconciliation_issues),
    )


def _overview_response(state: FactoryState) -> FactoryOverviewResponse:
    overview = state.overview
    return FactoryOverviewResponse(
        jobs_created=overview.jobs_created,
        completed_jobs=overview.completed_jobs,
        open_jobs=overview.open_jobs,
        overdue_open_jobs=overview.overdue_open_jobs,
        blocked_jobs=overview.blocked_jobs,
        late_completed_jobs=overview.late_completed_jobs,
        completed_quantity=overview.completed_quantity,
        good_quantity=overview.good_quantity,
        scrap_quantity=overview.scrap_quantity,
        aggregate_yield=overview.aggregate_yield,
        known_priced_work_at_risk=overview.known_priced_work_at_risk,
        priced_overdue_open_jobs=overview.priced_overdue_open_jobs,
        overdue_open_jobs_for_pricing=overview.overdue_open_jobs_for_pricing,
    )


def overview_response(state: FactoryState) -> OverviewResponse:
    return OverviewResponse(
        factory_as_of=state.factory_as_of,
        data_health=_data_health_response(state),
        overview=_overview_response(state),
    )


def attention_response(item: AttentionItem) -> AttentionResponse:
    return AttentionResponse(
        id=item.id,
        severity=item.severity,
        category=item.category,
        title=item.title,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        why_it_matters=item.why_it_matters,
        supporting_facts=dict(item.supporting_facts),
        evidence_event_ids=list(item.evidence_event_ids),
    )


def job_summary_response(job: JobState) -> JobSummaryResponse:
    return JobSummaryResponse(
        job_id=job.job_id,
        customer_id=job.customer_id,
        part_id=job.part_id,
        material=job.material,
        priority=job.priority,
        facility=job.facility,
        tool_id=job.tool_id,
        target_due_at=job.target_due_at,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        is_blocked=job.is_blocked,
        block_reason=job.block_reason,
        is_overdue=job.is_overdue,
        completed_late=job.completed_late,
        estimated_value=job.estimated_value,
    )


def _event_response(event: NormalizedEvent) -> EventResponse:
    return EventResponse(
        event_id=event.event_id,
        timestamp=event.timestamp,
        event_type=event.event_type,
        job_id=event.job_id,
        part_id=event.part_id,
        customer_id=event.customer_id,
        machine_id=event.machine_id,
        material=event.material,
        quantity=event.quantity,
        metadata=dict(event.metadata),
    )


def job_detail_response(state: FactoryState, job: JobState) -> JobDetailResponse:
    summary = job_summary_response(job)
    return JobDetailResponse(
        **summary.model_dump(),
        target_quantity=job.target_quantity,
        blocked_at=job.blocked_at,
        unit_price_estimate=job.unit_price_estimate,
        completed_quantity=job.completed_quantity,
        good_quantity=job.good_quantity,
        scrap_quantity=job.scrap_quantity,
        yield_rate=job.yield_rate,
        created_event_id=job.created_event_id,
        block_event_id=job.block_event_id,
        completion_event_id=job.completion_event_id,
        timeline=[_event_response(state.events_by_id[event_id]) for event_id in job.timeline_event_ids],
    )


def quality_response(state: FactoryState) -> QualityResponse:
    quality = state.quality
    return QualityResponse(
        inspection_passed_events=quality.inspection_passed_events,
        inspection_failed_events=quality.inspection_failed_events,
        inspection_event_pass_rate=quality.inspection_event_pass_rate,
        defect_counts=dict(quality.defect_counts),
    )


def create_app(test_config: RuntimeConfig | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = test_config if test_config is not None else load_runtime_config()
        ingestion = load_events(config.data_path)
        app.state.factory_state = project_factory_state(ingestion)
        app.state.internal_api_key = config.internal_api_key
        yield

    app = FastAPI(lifespan=lifespan)
    protected = APIRouter(dependencies=[Depends(require_internal_key)])

    @app.get("/health", response_model=HealthResponse)
    def health(state: FactoryStateDependency) -> HealthResponse:
        return HealthResponse(
            status="ready",
            factory_as_of=state.factory_as_of,
            source_sha256=state.source_sha256,
        )

    @protected.get("/overview", response_model=OverviewResponse)
    def overview(state: FactoryStateDependency) -> OverviewResponse:
        return overview_response(state)

    @protected.get("/attention", response_model=list[AttentionResponse])
    def attention(state: FactoryStateDependency) -> list[AttentionResponse]:
        return [attention_response(item) for item in state.attention]

    @protected.get("/jobs", response_model=list[JobSummaryResponse])
    def jobs(state: FactoryStateDependency) -> list[JobSummaryResponse]:
        return [job_summary_response(state.jobs[job_id]) for job_id in sorted(state.jobs)]

    @protected.get("/jobs/{job_id}", response_model=JobDetailResponse)
    def job_detail(job_id: str, state: FactoryStateDependency) -> JobDetailResponse:
        job = state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job_detail_response(state, job)

    @protected.get("/quality", response_model=QualityResponse)
    def quality(state: FactoryStateDependency) -> QualityResponse:
        return quality_response(state)

    app.include_router(protected)
    return app

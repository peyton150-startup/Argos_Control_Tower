from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from math import isfinite
from types import MappingProxyType

from app.domain import (
    AttentionItem,
    FactoryOverview,
    FactoryState,
    IngestionResult,
    JobState,
    NormalizedEvent,
    QualityState,
)

_ATTENTION_CATEGORY_RANK = {
    "BLOCKED_AND_OVERDUE": 0,
    "BLOCKED": 1,
    "OVERDUE": 2,
}
_PRIORITY_RANK = {"high": 0, "normal": 1, "low": 2}


@dataclass(slots=True)
class _JobAccumulator:
    created_event: NormalizedEvent
    started_at: datetime | None = None
    completed_at: datetime | None = None
    is_blocked: bool = False
    block_reason: str | None = None
    blocked_at: datetime | None = None
    block_event_id: str | None = None
    completion_event: NormalizedEvent | None = None
    timeline_event_ids: list[str] = field(default_factory=list)


def project_factory_state(ingestion: IngestionResult) -> FactoryState:
    """Project trusted events into deterministic factory lifecycle and operations state."""
    events = tuple(
        sorted(
            ingestion.trusted_events,
            key=lambda event: (event.timestamp, event.ingestion_index),
        )
    )
    _require_unique_event_ids(events)
    _require_unique_authoritative_events(events, "job_created")
    _require_unique_authoritative_events(events, "job_completed")

    creation_events: dict[str, NormalizedEvent] = {}
    reconciliation_issues: list[str] = []
    for event in events:
        if event.event_type == "job_created" and event.job_id is not None:
            creation_events.setdefault(event.job_id, event)

    jobs = {
        job_id: _JobAccumulator(created_event=created_event)
        for job_id, created_event in creation_events.items()
    }
    for event in events:
        if event.job_id is None or event.job_id not in jobs:
            continue

        job = jobs[event.job_id]
        job.timeline_event_ids.append(event.event_id)
        if (event.timestamp, event.ingestion_index) < (
            job.created_event.timestamp,
            job.created_event.ingestion_index,
        ):
            continue
        if event.event_type == "job_started" and job.started_at is None and job.completed_at is None:
            job.started_at = event.timestamp
        elif event.event_type == "job_blocked" and job.completed_at is None:
            reason = event.metadata.get("reason")
            job.is_blocked = True
            job.block_reason = reason if isinstance(reason, str) else None
            job.blocked_at = event.timestamp
            job.block_event_id = event.event_id
        elif event.event_type == "job_unblocked" and job.completed_at is None:
            job.is_blocked = False
            job.block_reason = None
            job.blocked_at = None
            job.block_event_id = None
        elif event.event_type == "job_completed" and job.completed_at is None:
            job.completed_at = event.timestamp
            job.completion_event = event
            job.is_blocked = False
            job.block_reason = None
            job.blocked_at = None
            job.block_event_id = None

    projected_jobs = {
        job_id: _project_job(job_id, job, ingestion.factory_as_of, reconciliation_issues)
        for job_id, job in jobs.items()
    }
    data_health = replace(
        ingestion.data_health,
        reconciliation_issues=ingestion.data_health.reconciliation_issues
        + tuple(reconciliation_issues),
    )
    return FactoryState(
        factory_as_of=ingestion.factory_as_of,
        source_sha256=ingestion.source_sha256,
        data_health=data_health,
        jobs=MappingProxyType(projected_jobs),
        events_by_id=MappingProxyType({event.event_id: event for event in events}),
        overview=_build_overview(tuple(projected_jobs.values())),
        quality=_build_quality(events),
        attention=_build_attention(tuple(projected_jobs.values())),
    )


def _project_job(
    job_id: str,
    job: _JobAccumulator,
    factory_as_of: datetime,
    reconciliation_issues: list[str],
) -> JobState:
    created = job.created_event
    priority = _optional_string(created.metadata.get("priority"))
    facility = _optional_string(created.metadata.get("facility"))
    tool_id = _optional_string(created.metadata.get("tool_id"))
    target_due_at = _parse_due_at(job_id, created.metadata.get("target_due_at"), reconciliation_issues)
    target_quantity = _parse_quantity(
        job_id, "target_quantity", created.metadata.get("target_quantity"), reconciliation_issues
    )
    unit_price_estimate = _parse_price(
        job_id, created.metadata.get("unit_price_estimate"), reconciliation_issues
    )
    estimated_value = (
        Decimal(target_quantity) * unit_price_estimate
        if target_quantity is not None and unit_price_estimate is not None
        else None
    )
    completed_quantity = good_quantity = scrap_quantity = None
    completion_event_id = None
    yield_rate = None
    if job.completion_event is not None:
        completion = job.completion_event
        completion_event_id = completion.event_id
        completed_quantity = _parse_quantity(
            job_id, "completed_quantity", completion.quantity, reconciliation_issues
        )
        good_quantity = _parse_quantity(
            job_id, "good_quantity", completion.metadata.get("good_quantity"), reconciliation_issues
        )
        scrap_quantity = _parse_quantity(
            job_id, "scrap_quantity", completion.metadata.get("scrap_quantity"), reconciliation_issues
        )
        if None not in (completed_quantity, good_quantity, scrap_quantity):
            if good_quantity + scrap_quantity == completed_quantity:
                if completed_quantity > 0:
                    yield_rate = Decimal(good_quantity) / Decimal(completed_quantity)
            else:
                reconciliation_issues.append(
                    f"job={job_id} field=completion_quantity reason=mismatch"
                )

    is_overdue = (
        job.completed_at is None
        and target_due_at is not None
        and target_due_at < factory_as_of
    )
    completed_late = (
        job.completed_at is not None
        and target_due_at is not None
        and job.completed_at > target_due_at
    )
    return JobState(
        job_id=job_id,
        customer_id=created.customer_id,
        part_id=created.part_id,
        material=created.material,
        created_at=created.timestamp,
        started_at=job.started_at,
        completed_at=job.completed_at,
        is_blocked=job.is_blocked,
        block_reason=job.block_reason,
        blocked_at=job.blocked_at,
        block_event_id=job.block_event_id,
        timeline_event_ids=tuple(job.timeline_event_ids),
        priority=priority,
        facility=facility,
        tool_id=tool_id,
        target_due_at=target_due_at,
        target_quantity=target_quantity,
        unit_price_estimate=unit_price_estimate,
        estimated_value=estimated_value,
        completed_quantity=completed_quantity,
        good_quantity=good_quantity,
        scrap_quantity=scrap_quantity,
        yield_rate=yield_rate,
        is_overdue=is_overdue,
        completed_late=completed_late,
        created_event_id=created.event_id,
        completion_event_id=completion_event_id,
    )


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _parse_due_at(
    job_id: str, value: object, reconciliation_issues: list[str]
) -> datetime | None:
    if not isinstance(value, str):
        reason = "missing" if value is None else "invalid_datetime"
        reconciliation_issues.append(f"job={job_id} field=target_due_at reason={reason}")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        reconciliation_issues.append(f"job={job_id} field=target_due_at reason=invalid_datetime")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        reconciliation_issues.append(f"job={job_id} field=target_due_at reason=naive_datetime")
        return None
    return parsed.astimezone(UTC)


def _parse_quantity(
    job_id: str, field: str, value: object, reconciliation_issues: list[str]
) -> int | None:
    if type(value) is int:
        return value
    reason = "missing" if value is None else "invalid_integer"
    reconciliation_issues.append(f"job={job_id} field={field} reason={reason}")
    return None


def _parse_price(
    job_id: str, value: object, reconciliation_issues: list[str]
) -> Decimal | None:
    if value is None:
        return None
    if type(value) is float and isfinite(value):
        return Decimal(str(value))
    reconciliation_issues.append(f"job={job_id} field=unit_price_estimate reason=invalid_money")
    return None


def _build_overview(jobs: tuple[JobState, ...]) -> FactoryOverview:
    completed_jobs = tuple(job for job in jobs if job.completed_at is not None)
    overdue_open_jobs = tuple(job for job in jobs if job.is_overdue)
    trusted_yield_jobs = tuple(job for job in completed_jobs if job.yield_rate is not None)
    completed_quantity = sum(job.completed_quantity or 0 for job in completed_jobs)
    good_quantity = sum(job.good_quantity or 0 for job in completed_jobs)
    scrap_quantity = sum(job.scrap_quantity or 0 for job in completed_jobs)
    trusted_completed_quantity = sum(job.completed_quantity or 0 for job in trusted_yield_jobs)
    trusted_good_quantity = sum(job.good_quantity or 0 for job in trusted_yield_jobs)
    priced_overdue_open_jobs = tuple(
        job for job in overdue_open_jobs if job.estimated_value is not None
    )
    return FactoryOverview(
        jobs_created=len(jobs),
        completed_jobs=len(completed_jobs),
        open_jobs=len(jobs) - len(completed_jobs),
        overdue_open_jobs=len(overdue_open_jobs),
        blocked_jobs=sum(job.is_blocked for job in jobs),
        late_completed_jobs=sum(job.completed_late for job in completed_jobs),
        completed_quantity=completed_quantity,
        good_quantity=good_quantity,
        scrap_quantity=scrap_quantity,
        aggregate_yield=(
            Decimal(trusted_good_quantity) / Decimal(trusted_completed_quantity)
            if trusted_completed_quantity > 0
            else None
        ),
        known_priced_work_at_risk=sum(
            (job.estimated_value for job in priced_overdue_open_jobs), start=Decimal(0)
        ),
        priced_overdue_open_jobs=len(priced_overdue_open_jobs),
        overdue_open_jobs_for_pricing=len(overdue_open_jobs),
    )


def _build_quality(events: tuple[NormalizedEvent, ...]) -> QualityState:
    passed_events = tuple(event for event in events if event.event_type == "inspection_passed")
    failed_events = tuple(event for event in events if event.event_type == "inspection_failed")
    defect_counts: dict[str, int] = {}
    for event in failed_events:
        defect_code = event.metadata.get("defect_code")
        if isinstance(defect_code, str):
            defect_counts[defect_code] = defect_counts.get(defect_code, 0) + 1
    total_events = len(passed_events) + len(failed_events)
    return QualityState.create(
        inspection_passed_events=len(passed_events),
        inspection_failed_events=len(failed_events),
        inspection_event_pass_rate=(
            Decimal(len(passed_events)) / Decimal(total_events) if total_events > 0 else None
        ),
        defect_counts=dict(sorted(defect_counts.items())),
    )


def _build_attention(jobs: tuple[JobState, ...]) -> tuple[AttentionItem, ...]:
    items = tuple(item for job in jobs if (item := _attention_for_job(job)) is not None)
    return tuple(sorted(items, key=_attention_sort_key))


def _attention_for_job(job: JobState) -> AttentionItem | None:
    if job.is_blocked and job.is_overdue:
        category = "BLOCKED_AND_OVERDUE"
        title = "Blocked and overdue job"
        why_it_matters = "The job has an active block and its target due time has passed."
    elif job.is_blocked:
        category = "BLOCKED"
        title = "Blocked job"
        why_it_matters = "The job has an active block."
    elif job.is_overdue:
        category = "OVERDUE"
        title = "Overdue job"
        why_it_matters = "The job's target due time has passed."
    else:
        return None

    supporting_facts: dict[str, str] = {}
    if job.target_due_at is not None:
        supporting_facts["target_due_at"] = job.target_due_at.isoformat()
    if job.is_blocked:
        supporting_facts["block_status"] = "active"
        if job.block_reason is not None:
            supporting_facts["block_reason"] = job.block_reason
    if job.priority is not None:
        supporting_facts["priority"] = job.priority
    if job.estimated_value is not None:
        supporting_facts["estimated_value"] = str(job.estimated_value)

    evidence_event_ids = (job.created_event_id,)
    if job.is_blocked and job.block_event_id is not None:
        evidence_event_ids += (job.block_event_id,)
    return AttentionItem.create(
        id=f"attention:{category.lower()}:{job.job_id}",
        severity="high",
        category=category,
        title=title,
        entity_type="job",
        entity_id=job.job_id,
        why_it_matters=why_it_matters,
        supporting_facts=supporting_facts,
        evidence_event_ids=evidence_event_ids,
    )


def _attention_sort_key(item: AttentionItem) -> tuple[object, ...]:
    due_at = item.supporting_facts.get("target_due_at")
    estimated_value = item.supporting_facts.get("estimated_value")
    return (
        _ATTENTION_CATEGORY_RANK[item.category],
        _PRIORITY_RANK.get(item.supporting_facts.get("priority"), len(_PRIORITY_RANK)),
        due_at is None,
        due_at or "",
        estimated_value is None,
        -Decimal(estimated_value) if estimated_value is not None else Decimal(0),
        item.entity_id,
    )


def _require_unique_event_ids(events: tuple[NormalizedEvent, ...]) -> None:
    event_ids = {event.event_id for event in events}
    if len(event_ids) != len(events):
        duplicate_ids = sorted(
            event_id for event_id in event_ids if sum(event.event_id == event_id for event in events) > 1
        )
        raise ValueError(f"Duplicate trusted event ID: {duplicate_ids[0]}")


def _require_unique_authoritative_events(
    events: tuple[NormalizedEvent, ...], event_type: str
) -> None:
    job_ids = [
        event.job_id
        for event in events
        if event.event_type == event_type and event.job_id is not None
    ]
    duplicate_job_ids = sorted(job_id for job_id in set(job_ids) if job_ids.count(job_id) > 1)
    if duplicate_job_ids:
        raise ValueError(f"Multiple trusted {event_type} events for job {duplicate_job_ids[0]!r}")

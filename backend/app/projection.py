from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from app.domain import FactoryState, IngestionResult, JobState, NormalizedEvent


@dataclass(slots=True)
class _JobAccumulator:
    created_event: NormalizedEvent
    started_at: datetime | None = None
    completed_at: datetime | None = None
    is_blocked: bool = False
    block_reason: str | None = None
    blocked_at: datetime | None = None
    block_event_id: str | None = None
    timeline_event_ids: list[str] = field(default_factory=list)


def project_factory_state(ingestion: IngestionResult) -> FactoryState:
    """Project trusted events into deterministic, lifecycle-only factory state."""
    events = tuple(
        sorted(
            ingestion.trusted_events,
            key=lambda event: (event.timestamp, event.ingestion_index),
        )
    )
    creation_events: dict[str, NormalizedEvent] = {}
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
            job.is_blocked = False
            job.block_reason = None
            job.blocked_at = None
            job.block_event_id = None

    projected_jobs = {
        job_id: JobState(
            job_id=job_id,
            customer_id=job.created_event.customer_id,
            part_id=job.created_event.part_id,
            material=job.created_event.material,
            created_at=job.created_event.timestamp,
            started_at=job.started_at,
            completed_at=job.completed_at,
            is_blocked=job.is_blocked,
            block_reason=job.block_reason,
            blocked_at=job.blocked_at,
            block_event_id=job.block_event_id,
            timeline_event_ids=tuple(job.timeline_event_ids),
        )
        for job_id, job in jobs.items()
    }
    return FactoryState(
        factory_as_of=ingestion.factory_as_of,
        source_sha256=ingestion.source_sha256,
        data_health=ingestion.data_health,
        jobs=MappingProxyType(projected_jobs),
        events_by_id=MappingProxyType({event.event_id: event for event in events}),
    )

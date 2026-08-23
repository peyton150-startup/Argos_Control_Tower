from datetime import UTC, datetime
from pathlib import Path

from app.domain import DataHealth, IngestionResult, NormalizedEvent
from app.projection import project_factory_state

TIMESTAMP = datetime(2026, 8, 1, 12, tzinfo=UTC)


def event(
    event_id: str,
    event_type: str,
    ingestion_index: int,
    *,
    timestamp: datetime = TIMESTAMP,
    job_id: str | None = "job-1",
    metadata: dict[str, str] | None = None,
) -> NormalizedEvent:
    return NormalizedEvent.create(
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        job_id=job_id,
        part_id="part-1",
        customer_id="customer-1",
        machine_id=None,
        material="carbon",
        quantity=None,
        metadata=metadata or {},
        ingestion_index=ingestion_index,
    )


def ingestion(
    *events: NormalizedEvent,
    factory_as_of: datetime = TIMESTAMP,
    source_sha256: str = "test-source",
) -> IngestionResult:
    return IngestionResult(
        trusted_events=events,
        quarantined_events=(),
        data_health=DataHealth(
            raw_rows=len(events),
            trusted_rows=len(events),
            duplicate_event_ids=0,
            exact_duplicate_copies=0,
            conflicting_duplicate_ids=0,
            quarantined_event_ids=(),
        ),
        factory_as_of=factory_as_of,
        source_sha256=source_sha256,
    )


def test_projection_is_independent_of_trusted_event_tuple_order() -> None:
    created = event("created", "job_created", 0)
    blocked = event("blocked", "job_blocked", 1, metadata={"reason": "missing_tool"})
    unblocked = event("unblocked", "job_unblocked", 2)

    ordered = project_factory_state(ingestion(created, blocked, unblocked))
    shuffled = project_factory_state(ingestion(unblocked, created, blocked))

    assert shuffled == ordered


def test_equal_timestamps_are_resolved_by_ingestion_index() -> None:
    created = event("created", "job_created", 0)
    blocked = event("blocked", "job_blocked", 2, metadata={"reason": "missing_tool"})
    unblocked = event("unblocked", "job_unblocked", 1)

    state = project_factory_state(ingestion(blocked, created, unblocked))

    assert state.jobs["job-1"].is_blocked is True
    assert state.jobs["job-1"].block_event_id == "blocked"


def test_block_then_unblock_clears_active_block_evidence() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0),
            event("blocked", "job_blocked", 1, metadata={"reason": "material_wait"}),
            event("unblocked", "job_unblocked", 2),
        )
    )

    job = state.jobs["job-1"]
    assert job.is_blocked is False
    assert job.block_reason is None
    assert job.blocked_at is None
    assert job.block_event_id is None


def test_completion_clears_active_block_evidence() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0),
            event("blocked", "job_blocked", 1, metadata={"reason": "machine_fault"}),
            event("completed", "job_completed", 2),
        )
    )

    job = state.jobs["job-1"]
    assert job.completed_at == TIMESTAMP
    assert job.is_blocked is False
    assert job.block_reason is None
    assert job.block_event_id is None


def test_job_hold_is_timeline_evidence_not_a_block_transition() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0),
            event("hold", "job_hold", 1),
        )
    )

    job = state.jobs["job-1"]
    assert job.is_blocked is False
    assert job.timeline_event_ids == ("created", "hold")


def test_unknown_job_events_do_not_synthesize_jobs() -> None:
    state = project_factory_state(
        ingestion(event("unknown-block", "job_blocked", 0, job_id="unknown"))
    )

    assert dict(state.jobs) == {}
    assert tuple(state.events_by_id) == ("unknown-block",)


def test_timeline_event_ids_follow_deterministic_lifecycle_order() -> None:
    state = project_factory_state(
        ingestion(
            event("completed", "job_completed", 3),
            event("started", "job_started", 1),
            event("created", "job_created", 0),
            event("hold", "job_hold", 2),
        )
    )

    assert state.jobs["job-1"].timeline_event_ids == (
        "created",
        "started",
        "hold",
        "completed",
    )


def test_factory_metadata_is_copied_unchanged() -> None:
    as_of = datetime(2026, 8, 2, 7, 30, tzinfo=UTC)
    source_sha256 = "a" * 64

    state = project_factory_state(
        ingestion(event("created", "job_created", 0), factory_as_of=as_of, source_sha256=source_sha256)
    )

    assert state.factory_as_of is as_of
    assert state.source_sha256 == source_sha256


def test_supplied_dataset_lifecycle_counts() -> None:
    from app.ingest import load_events

    result = load_events(Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl")

    state = project_factory_state(result)

    jobs = tuple(state.jobs.values())
    assert len(jobs) == 312
    assert sum(job.completed_at is not None for job in jobs) == 281
    assert sum(job.completed_at is None for job in jobs) == 31
    assert sum(job.is_blocked for job in jobs) == 9

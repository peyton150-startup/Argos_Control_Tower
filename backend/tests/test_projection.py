from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

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
    metadata: dict[str, object] | None = None,
    quantity: int | None = None,
    part_id: str | None = "part-1",
    customer_id: str | None = "customer-1",
    material: str | None = "carbon",
) -> NormalizedEvent:
    return NormalizedEvent.create(
        event_id=event_id,
        timestamp=timestamp,
        event_type=event_type,
        job_id=job_id,
        part_id=part_id,
        customer_id=customer_id,
        machine_id=None,
        material=material,
        quantity=quantity,
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
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-02T12:00:00Z", "target_quantity": 10},
            ),
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
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-02T12:00:00Z", "target_quantity": 10},
            ),
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


def test_duplicate_trusted_event_ids_are_rejected_before_projection_indexing() -> None:
    with pytest.raises(
        ValueError,
        match="Duplicate trusted event ID: duplicate",
    ):
        project_factory_state(
            ingestion(
                event("duplicate", "job_created", 0),
                event("duplicate", "job_started", 1),
            )
        )


def test_multiple_trusted_job_created_events_for_one_job_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Multiple trusted job_created events for job 'job-1'",
    ):
        project_factory_state(
            ingestion(
                event("created-1", "job_created", 0),
                event("created-2", "job_created", 1),
            )
        )


def test_multiple_trusted_job_completed_events_for_one_job_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Multiple trusted job_completed events for job 'job-1'",
    ):
        project_factory_state(
            ingestion(
                event("created", "job_created", 0),
                event("completed-1", "job_completed", 1),
                event("completed-2", "job_completed", 2),
            )
        )


def test_pre_creation_event_is_evidence_but_cannot_change_lifecycle_state() -> None:
    state = project_factory_state(
        ingestion(
            event("blocked-before-create", "job_blocked", 0, metadata={"reason": "missing_tool"}),
            event("created", "job_created", 1),
        )
    )

    job = state.jobs["job-1"]
    assert job.is_blocked is False
    assert job.block_event_id is None
    assert job.timeline_event_ids == ("blocked-before-create", "created")
    assert state.events_by_id["blocked-before-create"].event_type == "job_blocked"


def test_post_completion_lifecycle_events_remain_evidence_without_reopening_job() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0),
            event("completed", "job_completed", 1),
            event("started-after-completion", "job_started", 2),
            event(
                "blocked-after-completion",
                "job_blocked",
                3,
                metadata={"reason": "machine_fault"},
            ),
            event("unblocked-after-completion", "job_unblocked", 4),
        )
    )

    job = state.jobs["job-1"]
    assert job.completed_at == TIMESTAMP
    assert job.started_at is None
    assert job.is_blocked is False
    assert job.timeline_event_ids == (
        "created",
        "completed",
        "started-after-completion",
        "blocked-after-completion",
        "unblocked-after-completion",
    )
    assert state.events_by_id["blocked-after-completion"].event_type == "job_blocked"


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


def test_open_job_is_overdue_against_factory_clock() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-01T11:59:59Z"},
            ),
            factory_as_of=TIMESTAMP,
        )
    )

    assert state.jobs["job-1"].is_overdue is True


def test_due_at_factory_clock_is_not_overdue() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-01T12:00:00Z"},
            )
        )
    )

    assert state.jobs["job-1"].is_overdue is False


def test_completed_job_is_not_overdue() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-01T11:00:00Z"},
            ),
            event("completed", "job_completed", 1, timestamp=TIMESTAMP + timedelta(minutes=1)),
        )
    )

    assert state.jobs["job-1"].is_overdue is False


def test_completion_after_due_at_is_late() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-01T12:00:00Z"},
            ),
            event("completed", "job_completed", 1, timestamp=TIMESTAMP + timedelta(seconds=1)),
        )
    )

    assert state.jobs["job-1"].completed_late is True


def test_completion_at_due_at_is_not_late() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-01T12:00:00Z"},
            ),
            event("completed", "job_completed", 1),
        )
    )

    assert state.jobs["job-1"].completed_late is False


def test_creation_owns_contract_facts_and_authority_evidence() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={
                    "priority": "high",
                    "facility": "alpha",
                    "target_due_at": "2026-08-02T12:00:00Z",
                    "target_quantity": 10,
                    "tool_id": "tool-created",
                    "unit_price_estimate": 12.50,
                },
                customer_id="created-customer",
                part_id="created-part",
                material="created-material",
            ),
            event(
                "completed",
                "job_completed",
                1,
                metadata={"priority": "low", "target_quantity": 999, "good_quantity": 9, "scrap_quantity": 1},
                quantity=10,
                customer_id="completion-customer",
                part_id="completion-part",
                material="completion-material",
            ),
        )
    )

    job = state.jobs["job-1"]
    assert (job.customer_id, job.part_id, job.material) == (
        "created-customer",
        "created-part",
        "created-material",
    )
    assert (job.priority, job.facility, job.tool_id, job.target_quantity) == (
        "high",
        "alpha",
        "tool-created",
        10,
    )
    assert job.created_event_id == "created"


def test_completion_owns_final_quantities_and_authority_evidence() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0, quantity=999),
            event("completed", "job_completed", 1, quantity=10, metadata={"good_quantity": 9, "scrap_quantity": 1}),
        )
    )

    job = state.jobs["job-1"]
    assert (job.completed_quantity, job.good_quantity, job.scrap_quantity) == (10, 9, 1)
    assert job.completion_event_id == "completed"


def test_cycle_quantities_cannot_alter_completed_totals() -> None:
    state = project_factory_state(
        ingestion(
            event("created", "job_created", 0),
            event("cycle", "cycle_completed", 1, quantity=999),
            event("completed", "job_completed", 2, quantity=10, metadata={"good_quantity": 9, "scrap_quantity": 1}),
        )
    )

    assert state.overview.completed_quantity == 10


def test_quantity_mismatch_preserves_facts_but_excludes_job_from_yield() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-02T12:00:00Z", "target_quantity": 10},
            ),
            event("completed", "job_completed", 1, quantity=10, metadata={"good_quantity": 8, "scrap_quantity": 1}),
        )
    )

    job = state.jobs["job-1"]
    assert (job.completed_quantity, job.good_quantity, job.scrap_quantity, job.yield_rate) == (10, 8, 1, None)
    assert state.data_health.reconciliation_issues == ("job=job-1 field=completion_quantity reason=mismatch",)
    assert state.overview.aggregate_yield is None


def test_invalid_completion_quantities_are_not_repaired() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_due_at": "2026-08-02T12:00:00Z", "target_quantity": 10},
            ),
            event("completed", "job_completed", 1, quantity=10, metadata={"good_quantity": True, "scrap_quantity": 1}),
        )
    )

    job = state.jobs["job-1"]
    assert (job.completed_quantity, job.good_quantity, job.scrap_quantity, job.yield_rate) == (10, None, 1, None)
    assert state.data_health.reconciliation_issues == (
        "job=job-1 field=good_quantity reason=invalid_integer",
    )


def test_missing_price_remains_none() -> None:
    state = project_factory_state(
        ingestion(event("created", "job_created", 0, metadata={"target_quantity": 10}))
    )

    job = state.jobs["job-1"]
    assert (job.unit_price_estimate, job.estimated_value) == (None, None)


def test_float_price_uses_decimal_string_conversion() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_quantity": 3, "unit_price_estimate": 0.1},
            )
        )
    )

    job = state.jobs["job-1"]
    assert (job.unit_price_estimate, job.estimated_value) == (Decimal("0.1"), Decimal("0.3"))


def test_integer_price_is_not_an_observed_money_type() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"target_quantity": 3, "unit_price_estimate": 12},
            )
        )
    )

    job = state.jobs["job-1"]
    assert (job.unit_price_estimate, job.estimated_value) == (None, None)


def test_aggregate_yield_is_weighted_by_completed_quantity() -> None:
    state = project_factory_state(
        ingestion(
            event("created-1", "job_created", 0, job_id="job-1"),
            event("completed-1", "job_completed", 1, job_id="job-1", quantity=100, metadata={"good_quantity": 50, "scrap_quantity": 50}),
            event("created-2", "job_created", 2, job_id="job-2"),
            event("completed-2", "job_completed", 3, job_id="job-2", quantity=10, metadata={"good_quantity": 10, "scrap_quantity": 0}),
        )
    )

    assert state.overview.aggregate_yield == Decimal(60) / Decimal(110)


def test_all_overdue_open_jobs_are_in_pricing_coverage_denominator() -> None:
    state = project_factory_state(
        ingestion(
            event("created-priced", "job_created", 0, job_id="priced", metadata={"target_due_at": "2026-08-01T11:00:00Z", "target_quantity": 10, "unit_price_estimate": 12.5}),
            event("created-unpriced", "job_created", 1, job_id="unpriced", metadata={"target_due_at": "2026-08-01T11:00:00Z", "target_quantity": 10}),
        )
    )

    overview = state.overview
    assert (overview.overdue_open_jobs, overview.priced_overdue_open_jobs, overview.overdue_open_jobs_for_pricing) == (2, 1, 2)
    assert overview.known_priced_work_at_risk == Decimal("125.0")


def test_supplied_dataset_lifecycle_counts() -> None:
    from app.ingest import load_events

    result = load_events(Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl")

    state = project_factory_state(result)

    trusted_creation_events = tuple(
        event for event in result.trusted_events if event.event_type == "job_created"
    )
    trusted_completion_events = tuple(
        event for event in result.trusted_events if event.event_type == "job_completed"
    )
    jobs = tuple(state.jobs.values())
    assert len(trusted_creation_events) == 312
    assert len({event.job_id for event in trusted_creation_events}) == 312
    assert len(jobs) == 312
    assert len(trusted_completion_events) == 281
    assert len({event.job_id for event in trusted_completion_events}) == 281
    assert sum(job.completed_at is not None for job in jobs) == 281
    assert sum(job.completed_at is None for job in jobs) == 31
    assert sum(job.is_blocked for job in jobs) == 9


def test_supplied_dataset_projection_b_acceptance_values() -> None:
    from app.ingest import load_events

    state = project_factory_state(
        load_events(Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl")
    )

    overview = state.overview
    assert overview.jobs_created == 312
    assert overview.completed_jobs == 281
    assert overview.open_jobs == 31
    assert overview.overdue_open_jobs == 26
    assert overview.blocked_jobs == 9
    assert overview.late_completed_jobs == 75
    assert overview.completed_quantity == 86_168
    assert overview.good_quantity == 78_555
    assert overview.scrap_quantity == 7_613
    assert overview.aggregate_yield == Decimal(78_555) / Decimal(86_168)
    assert overview.known_priced_work_at_risk == Decimal("590465.02")
    assert (overview.priced_overdue_open_jobs, overview.overdue_open_jobs_for_pricing) == (10, 26)


def test_supplied_dataset_quality_reproduces_trusted_defect_baseline() -> None:
    from app.ingest import load_events

    state = project_factory_state(
        load_events(Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl")
    )

    assert dict(state.quality.defect_counts) == {
        "voids": 827,
        "delamination": 421,
        "dimensional": 347,
        "surface": 337,
        "resin_rich": 244,
        "other": 212,
    }


def test_quality_counts_trusted_inspection_events_and_uses_exact_event_pass_rate() -> None:
    state = project_factory_state(
        ingestion(
            event("pass-1", "inspection_passed", 0, quantity=10),
            event("pass-2", "inspection_passed", 1, quantity=1),
            event("failed", "inspection_failed", 2, quantity=99, metadata={"defect_code": "voids"}),
        )
    )

    assert state.quality.inspection_passed_events == 2
    assert state.quality.inspection_failed_events == 1
    assert state.quality.inspection_event_pass_rate == Decimal(2) / Decimal(3)


def test_attention_order_is_deterministic_under_input_permutation() -> None:
    future_due = "2026-08-02T12:00:00Z"
    overdue_due = "2026-07-31T12:00:00Z"
    events = (
        event(
            "created-combined",
            "job_created",
            0,
            job_id="combined",
            metadata={"priority": "low", "target_due_at": overdue_due},
        ),
        event("blocked-combined", "job_blocked", 1, job_id="combined"),
        event(
            "created-blocked-high",
            "job_created",
            2,
            job_id="blocked-high",
            metadata={"priority": "high", "target_due_at": future_due},
        ),
        event("blocked-high", "job_blocked", 3, job_id="blocked-high"),
        event(
            "created-blocked-low",
            "job_created",
            4,
            job_id="blocked-low",
            metadata={"priority": "low", "target_due_at": future_due},
        ),
        event("blocked-low", "job_blocked", 5, job_id="blocked-low"),
        event(
            "created-overdue-high",
            "job_created",
            6,
            job_id="overdue-high",
            metadata={"priority": "high", "target_due_at": overdue_due},
        ),
        event(
            "created-overdue-low",
            "job_created",
            7,
            job_id="overdue-low",
            metadata={"priority": "low", "target_due_at": overdue_due},
        ),
    )

    ordered = project_factory_state(ingestion(*events))
    shuffled = project_factory_state(ingestion(*reversed(events)))

    expected_ids = (
        "attention:blocked_and_overdue:combined",
        "attention:blocked:blocked-high",
        "attention:blocked:blocked-low",
        "attention:overdue:overdue-high",
        "attention:overdue:overdue-low",
    )
    assert tuple(item.id for item in ordered.attention) == expected_ids
    assert shuffled.attention == ordered.attention


def test_attention_classifies_blocked_and_overdue_with_creation_and_active_block_evidence() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"priority": "normal", "target_due_at": "2026-07-31T12:00:00Z"},
            ),
            event("blocked", "job_blocked", 1, metadata={"reason": "material_wait"}),
        )
    )

    item = state.attention[0]
    assert (item.category, item.entity_type, item.entity_id) == (
        "BLOCKED_AND_OVERDUE",
        "job",
        "job-1",
    )
    assert item.evidence_event_ids == ("created", "blocked")


def test_attention_classifies_simple_blocked_job() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"priority": "normal", "target_due_at": "2026-08-02T12:00:00Z"},
            ),
            event("blocked", "job_blocked", 1, metadata={"reason": "missing_tool"}),
        )
    )

    assert tuple(item.category for item in state.attention) == ("BLOCKED",)


def test_attention_classifies_simple_overdue_job() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created",
                "job_created",
                0,
                metadata={"priority": "normal", "target_due_at": "2026-07-31T12:00:00Z"},
            )
        )
    )

    assert tuple(item.category for item in state.attention) == ("OVERDUE",)


def test_attention_evidence_ids_resolve_from_factory_events() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "created-blocked",
                "job_created",
                0,
                job_id="blocked",
                metadata={"target_due_at": "2026-08-02T12:00:00Z"},
            ),
            event("blocked", "job_blocked", 1, job_id="blocked"),
            event(
                "created-overdue",
                "job_created",
                2,
                job_id="overdue",
                metadata={"target_due_at": "2026-07-31T12:00:00Z"},
            ),
        )
    )

    assert all(
        evidence_id in state.events_by_id
        for item in state.attention
        for evidence_id in item.evidence_event_ids
    )


def test_quarantined_inspection_records_cannot_change_quality_totals() -> None:
    trusted = event("trusted-pass", "inspection_passed", 0, quantity=1)
    quarantined = event(
        "quarantined-failure",
        "inspection_failed",
        1,
        quantity=100,
        metadata={"defect_code": "voids"},
    )
    source = ingestion(trusted)
    state = project_factory_state(
        IngestionResult(
            trusted_events=source.trusted_events,
            quarantined_events=(quarantined,),
            data_health=source.data_health,
            factory_as_of=source.factory_as_of,
            source_sha256=source.source_sha256,
        )
    )

    assert (state.quality.inspection_passed_events, state.quality.inspection_failed_events) == (1, 0)
    assert dict(state.quality.defect_counts) == {}


def test_resin_rich_remains_a_defect_category_only() -> None:
    state = project_factory_state(
        ingestion(
            event(
                "resin-rich-failure",
                "inspection_failed",
                0,
                quantity=1,
                metadata={"defect_code": "resin_rich"},
            )
        )
    )

    assert dict(state.quality.defect_counts) == {"resin_rich": 1}
    assert not hasattr(state.quality, "resin_percentage")

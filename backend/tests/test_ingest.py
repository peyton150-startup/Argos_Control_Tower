import json
from pathlib import Path

import polars as pl
import pytest

from app.ingest import load_events

DATA_PATH = Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl"


CREATED_EVENT = {
    "event_id": "evt-1",
    "timestamp": "2026-01-01T12:00:00Z",
    "event_type": "job_created",
    "job_id": "job-1",
    "part_id": "part-1",
    "customer_id": "customer-1",
    "machine_id": None,
    "material": "carbon_fiber_epoxy",
    "quantity": 10,
    "metadata": {
        "priority": "normal",
        "facility": "la_01",
        "target_due_at": "2026-01-02T12:00:00Z",
        "target_quantity": 10,
    },
}


def write_jsonl(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "".join(f"{json.dumps(record, separators=(',', ':'))}\n" for record in records),
        encoding="utf-8",
    )
    return path


def test_exact_duplicate_copy_collapses_to_one_trusted_event(tmp_path: Path) -> None:
    result = load_events(write_jsonl(tmp_path, [CREATED_EVENT, CREATED_EVENT]))

    assert tuple(event.event_id for event in result.trusted_events) == ("evt-1",)
    assert result.data_health.raw_rows == 2
    assert result.data_health.trusted_rows == 1
    assert result.data_health.duplicate_event_ids == 1
    assert result.data_health.exact_duplicate_copies == 1
    assert result.data_health.conflicting_duplicate_ids == 0
    assert result.quarantined_events == ()


def test_conflicting_event_id_quarantines_every_copy(tmp_path: Path) -> None:
    conflicting_event = {**CREATED_EVENT, "quantity": 99}

    result = load_events(write_jsonl(tmp_path, [CREATED_EVENT, conflicting_event]))

    assert result.trusted_events == ()
    assert tuple(event.quantity for event in result.quarantined_events) == (10, 99)
    assert result.data_health.raw_rows == 2
    assert result.data_health.trusted_rows == 0
    assert result.data_health.duplicate_event_ids == 1
    assert result.data_health.exact_duplicate_copies == 0
    assert result.data_health.conflicting_duplicate_ids == 1
    assert result.data_health.quarantined_event_ids == ("evt-1",)


def test_repeated_load_returns_the_same_trusted_boundary(tmp_path: Path) -> None:
    path = write_jsonl(tmp_path, [CREATED_EVENT])

    assert load_events(path) == load_events(path)


def test_source_rows_are_stable_when_timestamps_are_not_ordered(tmp_path: Path) -> None:
    earlier_event = {
        **CREATED_EVENT,
        "event_id": "evt-2",
        "timestamp": "2025-12-31T12:00:00Z",
    }

    result = load_events(write_jsonl(tmp_path, [CREATED_EVENT, earlier_event]))

    assert tuple(event.event_id for event in result.trusted_events) == ("evt-1", "evt-2")
    assert tuple(event.ingestion_index for event in result.trusted_events) == (0, 1)


def test_late_appearing_metadata_survives_full_schema_inference(tmp_path: Path) -> None:
    early_events = [{**CREATED_EVENT, "event_id": f"evt-{index}"} for index in range(100)]
    late_event = {
        **CREATED_EVENT,
        "event_id": "evt-late",
        "metadata": {**CREATED_EVENT["metadata"], "inspector": "qa-7"},
    }

    result = load_events(write_jsonl(tmp_path, [*early_events, late_event]))

    assert result.trusted_events[-1].metadata["inspector"] == "qa-7"


def test_invalid_json_fails_visibly(tmp_path: Path) -> None:
    path = tmp_path / "invalid.jsonl"
    path.write_text('{"event_id":', encoding="utf-8")

    with pytest.raises(pl.exceptions.ComputeError):
        load_events(path)


def test_supplied_dataset_reproduces_trusted_ingestion_baseline() -> None:
    result = load_events(DATA_PATH)

    assert result.source_sha256 == "454cc6fb14851c392742af9d3deec2a1b6203b0f6e1f167c38d2f4027594eae7"
    assert result.data_health.raw_rows == 19_519
    assert result.data_health.trusted_rows == 19_495
    assert result.data_health.duplicate_event_ids == 19
    assert result.data_health.exact_duplicate_copies == 14
    assert result.data_health.conflicting_duplicate_ids == 5
    assert result.data_health.quarantined_event_ids == (
        "evt_005087",
        "evt_009610",
        "evt_009935",
        "evt_014575",
        "evt_014986",
    )
    assert len(result.quarantined_events) == 10
    assert result.factory_as_of.isoformat() == "2026-08-13T23:06:33+00:00"

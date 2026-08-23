from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import polars as pl

from app.domain import DataHealth, IngestionResult, MetadataValue, NormalizedEvent

REQUIRED_COLUMNS = {
    "event_id",
    "timestamp",
    "event_type",
    "job_id",
    "part_id",
    "customer_id",
    "machine_id",
    "material",
    "quantity",
    "metadata",
}


def load_events(path: Path) -> IngestionResult:
    lazy_frame = pl.scan_ndjson(path, infer_schema_length=None, ignore_errors=False)
    missing_columns = REQUIRED_COLUMNS.difference(lazy_frame.collect_schema().names())
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required event columns: {missing}")

    frame = (
        lazy_frame.with_row_index("ingestion_index")
        .with_columns(pl.col("timestamp").str.to_datetime(strict=True, time_zone="UTC"))
        .collect()
    )
    if frame.height == 0:
        raise ValueError("Event dataset is empty")

    events = tuple(_normalize_row(row) for row in frame.iter_rows(named=True))
    trusted, quarantined, health = _classify_duplicates(events)
    return IngestionResult(
        trusted_events=trusted,
        quarantined_events=quarantined,
        data_health=health,
        factory_as_of=max(event.timestamp for event in events),
    )


def _normalize_row(row: dict[str, object]) -> NormalizedEvent:
    metadata = row["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError(f"Event {row['event_id']!r} metadata must be an object")

    return NormalizedEvent.create(
        event_id=_required_string(row, "event_id"),
        timestamp=_required_datetime(row, "timestamp"),
        event_type=_required_string(row, "event_type"),
        job_id=_optional_string(row, "job_id"),
        part_id=_optional_string(row, "part_id"),
        customer_id=_optional_string(row, "customer_id"),
        machine_id=_optional_string(row, "machine_id"),
        material=_optional_string(row, "material"),
        quantity=_optional_integer(row, "quantity"),
        metadata=_normalize_metadata(metadata, str(row["event_id"])),
        ingestion_index=_required_integer(row, "ingestion_index"),
    )


def _classify_duplicates(
    events: Iterable[NormalizedEvent],
) -> tuple[tuple[NormalizedEvent, ...], tuple[NormalizedEvent, ...], DataHealth]:
    event_list = tuple(events)
    by_id: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for event in event_list:
        by_id[event.event_id].append(event)

    trusted: list[NormalizedEvent] = []
    quarantined: list[NormalizedEvent] = []
    exact_duplicate_copies = 0
    conflicting_ids: list[str] = []
    duplicate_event_ids = 0

    for event_id, copies in by_id.items():
        if len(copies) == 1:
            trusted.append(copies[0])
            continue

        duplicate_event_ids += 1
        if len({_canonical_payload(copy) for copy in copies}) == 1:
            trusted.append(copies[0])
            exact_duplicate_copies += len(copies) - 1
        else:
            conflicting_ids.append(event_id)
            quarantined.extend(copies)

    trusted.sort(key=lambda event: event.ingestion_index)
    quarantined.sort(key=lambda event: event.ingestion_index)
    conflicting_ids.sort()
    health = DataHealth(
        raw_rows=len(event_list),
        trusted_rows=len(trusted),
        duplicate_event_ids=duplicate_event_ids,
        exact_duplicate_copies=exact_duplicate_copies,
        conflicting_duplicate_ids=len(conflicting_ids),
        quarantined_event_ids=tuple(conflicting_ids),
    )
    return tuple(trusted), tuple(quarantined), health


def _canonical_payload(event: NormalizedEvent) -> str:
    payload = {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type,
        "job_id": event.job_id,
        "part_id": event.part_id,
        "customer_id": event.customer_id,
        "machine_id": event.machine_id,
        "material": event.material,
        "quantity": event.quantity,
        "metadata": dict(event.metadata),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _normalize_metadata(metadata: dict[str, object], event_id: str) -> dict[str, MetadataValue]:
    normalized: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ValueError(f"Event {event_id!r} metadata keys must be strings")
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"Event {event_id!r} metadata field {key!r} is not scalar")
        normalized[key] = value
    return normalized


def _required_string(row: dict[str, object], field: str) -> str:
    value = row[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"Event field {field!r} must be a non-empty string")
    return value


def _optional_string(row: dict[str, object], field: str) -> str | None:
    value = row[field]
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Event field {field!r} must be a string or null")
    return value


def _required_datetime(row: dict[str, object], field: str) -> datetime:
    value = row[field]
    if not isinstance(value, datetime):
        raise ValueError(f"Event field {field!r} must be a timestamp")
    return value


def _required_integer(row: dict[str, object], field: str) -> int:
    value = row[field]
    if not isinstance(value, int):
        raise ValueError(f"Event field {field!r} must be an integer")
    return value


def _optional_integer(row: dict[str, object], field: str) -> int | None:
    value = row[field]
    if value is not None and not isinstance(value, int):
        raise ValueError(f"Event field {field!r} must be an integer or null")
    return value

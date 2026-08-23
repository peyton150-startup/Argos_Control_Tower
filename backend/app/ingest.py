from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import file_digest
from pathlib import Path

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
    source_sha256 = _source_sha256(path)
    rows = tuple(_read_jsonl(path))
    if not rows:
        raise ValueError("Event dataset is empty")
    events = tuple(_normalize_row(row) for row in rows)
    trusted, quarantined, health = _classify_duplicates(events)
    if not trusted:
        raise ValueError("No trusted events remain for authoritative factory clock")
    return IngestionResult(
        trusted_events=trusted,
        quarantined_events=quarantined,
        data_health=health,
        factory_as_of=max(event.timestamp for event in trusted),
        source_sha256=source_sha256,
    )


def _read_jsonl(path: Path) -> Iterable[dict[str, object]]:
    with path.open(encoding="utf-8") as source:
        for ingestion_index, line in enumerate(source):
            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError("Event row must be an object")
            missing_columns = REQUIRED_COLUMNS.difference(row)
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(f"Missing required event columns: {missing}")
            timestamp = row["timestamp"]
            if not isinstance(timestamp, str):
                raise TypeError("Event field 'timestamp' must be an ISO timestamp string")
            parsed_timestamp = datetime.fromisoformat(timestamp)
            if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
                raise ValueError("Event field 'timestamp' must include a timezone")
            yield {
                **row,
                "timestamp": parsed_timestamp.astimezone(UTC),
                "ingestion_index": ingestion_index,
            }


def _source_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def _normalize_row(row: dict[str, object]) -> NormalizedEvent:
    metadata = row["metadata"]
    if not isinstance(metadata, dict):
        raise TypeError(f"Event {row['event_id']!r} metadata must be an object")

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
            raise TypeError(f"Event {event_id!r} metadata keys must be strings")
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
        raise TypeError(f"Event field {field!r} must be a timestamp")
    return value


def _required_integer(row: dict[str, object], field: str) -> int:
    value = row[field]
    if not isinstance(value, int):
        raise TypeError(f"Event field {field!r} must be an integer")
    return value


def _optional_integer(row: dict[str, object], field: str) -> int | None:
    value = row[field]
    if value is not None and not isinstance(value, int):
        raise ValueError(f"Event field {field!r} must be an integer or null")
    return value

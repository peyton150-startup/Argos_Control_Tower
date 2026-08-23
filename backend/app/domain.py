from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

MetadataValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class NormalizedEvent:
    event_id: str
    timestamp: datetime
    event_type: str
    job_id: str | None
    part_id: str | None
    customer_id: str | None
    machine_id: str | None
    material: str | None
    quantity: int | None
    metadata: Mapping[str, MetadataValue]
    ingestion_index: int

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        timestamp: datetime,
        event_type: str,
        job_id: str | None,
        part_id: str | None,
        customer_id: str | None,
        machine_id: str | None,
        material: str | None,
        quantity: int | None,
        metadata: Mapping[str, MetadataValue],
        ingestion_index: int,
    ) -> NormalizedEvent:
        return cls(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            job_id=job_id,
            part_id=part_id,
            customer_id=customer_id,
            machine_id=machine_id,
            material=material,
            quantity=quantity,
            metadata=MappingProxyType(dict(metadata)),
            ingestion_index=ingestion_index,
        )


@dataclass(frozen=True, slots=True)
class DataHealth:
    raw_rows: int
    trusted_rows: int
    duplicate_event_ids: int
    exact_duplicate_copies: int
    conflicting_duplicate_ids: int
    quarantined_event_ids: tuple[str, ...]
    validation_issue_count: int = 0
    reconciliation_issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IngestionResult:
    trusted_events: tuple[NormalizedEvent, ...]
    quarantined_events: tuple[NormalizedEvent, ...]
    data_health: DataHealth
    factory_as_of: datetime


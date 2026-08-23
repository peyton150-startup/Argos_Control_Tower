from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import RuntimeConfig, create_app, load_runtime_config


def write_jsonl(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "events.jsonl"
    path.write_text(
        "".join(f"{json.dumps(record, separators=(',', ':'))}\n" for record in records),
        encoding="utf-8",
    )
    return path


def event(
    event_id: str,
    event_type: str,
    timestamp: str,
    *,
    job_id: str | None = "job-2",
    metadata: dict[str, object] | None = None,
    quantity: int | None = None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "job_id": job_id,
        "part_id": "part-2" if job_id else None,
        "customer_id": "customer-2" if job_id else None,
        "machine_id": "machine-2" if job_id else None,
        "material": "carbon_fiber" if job_id else None,
        "quantity": quantity,
        "metadata": metadata or {},
    }


@pytest.fixture
def api_app(tmp_path: Path):
    data_path = write_jsonl(
        tmp_path,
        [
            event(
                "created-job-2",
                "job_created",
                "2026-08-01T10:00:00Z",
                metadata={
                    "priority": "high",
                    "facility": "alpha",
                    "tool_id": "tool-2",
                    "target_due_at": "2026-08-01T10:01:00Z",
                    "target_quantity": 3,
                    "unit_price_estimate": 12.5,
                },
            ),
            event(
                "created-job-1",
                "job_created",
                "2026-08-01T10:01:00Z",
                job_id="job-1",
                metadata={
                    "priority": "normal",
                    "target_due_at": "2026-08-02T10:00:00Z",
                    "target_quantity": 10,
                },
            ),
            event(
                "blocked-job-2",
                "job_blocked",
                "2026-08-01T10:02:00Z",
                metadata={"reason": "missing_tool"},
            ),
            event(
                "inspection-pass",
                "inspection_passed",
                "2026-08-01T10:03:00Z",
                job_id=None,
            ),
            event(
                "inspection-fail",
                "inspection_failed",
                "2026-08-01T10:04:00Z",
                job_id=None,
                metadata={"defect_code": "voids"},
            ),
            event(
                "completed-job-1",
                "job_completed",
                "2026-08-01T10:05:00Z",
                job_id="job-1",
                metadata={"good_quantity": 8, "scrap_quantity": 2},
                quantity=10,
            ),
        ],
    )
    return create_app(RuntimeConfig(data_path=data_path, internal_api_key="test-secret"))


def test_main_import_has_no_configuration_or_data_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    module = importlib.import_module("app.main")

    assert module.app is not None


def test_lifespan_projects_factory_state_once(api_app) -> None:
    with TestClient(api_app) as client:
        first_state = api_app.state.factory_state
        assert client.get("/health").status_code == 200
        assert api_app.state.factory_state is first_state


def test_runtime_config_requires_nonblank_internal_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="INTERNAL_API_KEY"):
        load_runtime_config()

    monkeypatch.setenv("INTERNAL_API_KEY", "   ")
    with pytest.raises(RuntimeError, match="INTERNAL_API_KEY"):
        load_runtime_config()


def test_runtime_config_resolves_relative_data_path_from_backend_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTERNAL_API_KEY", "test-secret")
    monkeypatch.setenv("DATA_PATH", "data/manufacturing_events.jsonl")

    config = load_runtime_config()

    assert config.data_path == Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl"


def test_startup_fails_for_missing_data_and_projection_invariant(tmp_path: Path) -> None:
    missing = create_app(RuntimeConfig(tmp_path / "missing.jsonl", "test-secret"))
    with pytest.raises(FileNotFoundError), TestClient(missing):
        pass

    invalid_path = write_jsonl(
        tmp_path,
        [
            event("created-1", "job_created", "2026-08-01T10:00:00Z", job_id="same"),
            event("created-2", "job_created", "2026-08-01T10:01:00Z", job_id="same"),
        ],
    )
    invalid = create_app(RuntimeConfig(invalid_path, "test-secret"))
    with pytest.raises(ValueError, match="Multiple trusted job_created"), TestClient(invalid):
        pass


def test_health_is_public_and_product_routes_require_the_same_unauthorized_response(api_app) -> None:
    with TestClient(api_app) as client:
        health = client.get("/health")
        missing = client.get("/overview")
        wrong = client.get("/overview", headers={"X-Internal-Key": "wrong"})
        correct = client.get("/overview", headers={"X-Internal-Key": "test-secret"})

    assert health.status_code == 200
    assert health.json() == {
        "status": "ready",
        "factory_as_of": "2026-08-01T10:05:00Z",
        "source_sha256": health.json()["source_sha256"],
    }
    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"detail": "Not authenticated"}
    assert missing.headers["www-authenticate"] == wrong.headers["www-authenticate"] == "APIKey"
    assert correct.status_code == 200


def test_overview_exactly_maps_projected_data_health_and_overview(api_app) -> None:
    with TestClient(api_app) as client:
        response = client.get("/overview", headers={"X-Internal-Key": "test-secret"})

    assert response.status_code == 200
    assert response.json() == {
        "factory_as_of": "2026-08-01T10:05:00Z",
        "data_health": {
            "raw_rows": 6,
            "trusted_rows": 6,
            "duplicate_event_ids": 0,
            "exact_duplicate_copies": 0,
            "conflicting_duplicate_ids": 0,
            "quarantined_event_ids": [],
            "validation_issue_count": 0,
            "reconciliation_issues": [],
        },
        "overview": {
            "jobs_created": 2,
            "completed_jobs": 1,
            "open_jobs": 1,
            "overdue_open_jobs": 1,
            "blocked_jobs": 1,
            "late_completed_jobs": 0,
            "completed_quantity": 10,
            "good_quantity": 8,
            "scrap_quantity": 2,
            "aggregate_yield": "0.8",
            "known_priced_work_at_risk": "37.5",
            "priced_overdue_open_jobs": 1,
            "overdue_open_jobs_for_pricing": 1,
        },
    }


def test_attention_preserves_projection_order_and_facts(api_app) -> None:
    with TestClient(api_app) as client:
        response = client.get("/attention", headers={"X-Internal-Key": "test-secret"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "attention:blocked_and_overdue:job-2",
            "severity": "high",
            "category": "BLOCKED_AND_OVERDUE",
            "title": "Blocked and overdue job",
            "entity_type": "job",
            "entity_id": "job-2",
            "why_it_matters": "The job has an active block and its target due time has passed.",
            "supporting_facts": {
                "target_due_at": "2026-08-01T10:01:00+00:00",
                "block_status": "active",
                "block_reason": "missing_tool",
                "priority": "high",
                "estimated_value": "37.5",
            },
            "evidence_event_ids": ["created-job-2", "blocked-job-2"],
        }
    ]


def test_jobs_are_sorted_by_job_id_and_detail_preserves_evidence_timeline(api_app) -> None:
    with TestClient(api_app) as client:
        jobs = client.get("/jobs", headers={"X-Internal-Key": "test-secret"})
        detail = client.get("/jobs/job-2", headers={"X-Internal-Key": "test-secret"})

    assert jobs.status_code == detail.status_code == 200
    assert [job["job_id"] for job in jobs.json()] == ["job-1", "job-2"]
    assert jobs.json()[1] == {
        "job_id": "job-2",
        "customer_id": "customer-2",
        "part_id": "part-2",
        "material": "carbon_fiber",
        "priority": "high",
        "facility": "alpha",
        "tool_id": "tool-2",
        "target_due_at": "2026-08-01T10:01:00Z",
        "created_at": "2026-08-01T10:00:00Z",
        "started_at": None,
        "completed_at": None,
        "is_blocked": True,
        "block_reason": "missing_tool",
        "is_overdue": True,
        "completed_late": False,
        "estimated_value": "37.5",
    }
    assert detail.json() == {
        "job_id": "job-2",
        "customer_id": "customer-2",
        "part_id": "part-2",
        "material": "carbon_fiber",
        "priority": "high",
        "facility": "alpha",
        "tool_id": "tool-2",
        "created_at": "2026-08-01T10:00:00Z",
        "started_at": None,
        "completed_at": None,
        "target_due_at": "2026-08-01T10:01:00Z",
        "target_quantity": 3,
        "is_blocked": True,
        "block_reason": "missing_tool",
        "blocked_at": "2026-08-01T10:02:00Z",
        "is_overdue": True,
        "completed_late": False,
        "unit_price_estimate": "12.5",
        "estimated_value": "37.5",
        "completed_quantity": None,
        "good_quantity": None,
        "scrap_quantity": None,
        "yield_rate": None,
        "created_event_id": "created-job-2",
        "block_event_id": "blocked-job-2",
        "completion_event_id": None,
        "timeline": [
            {
                "event_id": "created-job-2",
                "timestamp": "2026-08-01T10:00:00Z",
                "event_type": "job_created",
                "job_id": "job-2",
                "part_id": "part-2",
                "customer_id": "customer-2",
                "machine_id": "machine-2",
                "material": "carbon_fiber",
                "quantity": None,
                "metadata": {
                    "priority": "high",
                    "facility": "alpha",
                    "tool_id": "tool-2",
                    "target_due_at": "2026-08-01T10:01:00Z",
                    "target_quantity": 3,
                    "unit_price_estimate": 12.5,
                    "reason": None,
                    "defect_code": None,
                    "good_quantity": None,
                    "scrap_quantity": None,
                },
            },
            {
                "event_id": "blocked-job-2",
                "timestamp": "2026-08-01T10:02:00Z",
                "event_type": "job_blocked",
                "job_id": "job-2",
                "part_id": "part-2",
                "customer_id": "customer-2",
                "machine_id": "machine-2",
                "material": "carbon_fiber",
                "quantity": None,
                    "metadata": {
                        "priority": None,
                        "facility": None,
                        "tool_id": None,
                        "target_due_at": None,
                        "target_quantity": None,
                        "unit_price_estimate": None,
                        "reason": "missing_tool",
                        "defect_code": None,
                        "good_quantity": None,
                        "scrap_quantity": None,
                    },
            },
        ],
    }


def test_unknown_job_returns_404(api_app) -> None:
    with TestClient(api_app) as client:
        response = client.get("/jobs/missing", headers={"X-Internal-Key": "test-secret"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


def test_quality_exactly_maps_projection_and_decimal_datetime_wire_contract(api_app) -> None:
    with TestClient(api_app) as client:
        quality = client.get("/quality", headers={"X-Internal-Key": "test-secret"})
        detail = client.get("/jobs/job-1", headers={"X-Internal-Key": "test-secret"})

    assert quality.status_code == detail.status_code == 200
    assert quality.json() == {
        "inspection_passed_events": 1,
        "inspection_failed_events": 1,
        "inspection_event_pass_rate": "0.5",
        "defect_counts": {"voids": 1},
    }
    assert detail.json()["yield_rate"] == "0.8"
    assert detail.json()["created_at"] == datetime(2026, 8, 1, 10, 1, tzinfo=UTC).isoformat().replace(
        "+00:00", "Z"
    )


def test_openapi_exposes_only_expected_paths_and_api_key_security(api_app) -> None:
    schema = api_app.openapi()

    assert set(schema["paths"]) == {"/health", "/overview", "/attention", "/jobs", "/jobs/{job_id}", "/quality"}
    assert schema["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey",
        "in": "header",
        "name": "X-Internal-Key",
    }
    assert "security" not in schema["paths"]["/health"]["get"]
    for path in ("/overview", "/attention", "/jobs", "/jobs/{job_id}", "/quality"):
        assert schema["paths"][path]["get"]["security"] == [{"APIKeyHeader": []}]


def test_real_data_overview_acceptance_loads_once() -> None:
    data_path = Path(__file__).parents[1] / "data" / "manufacturing_events.jsonl"
    app = create_app(RuntimeConfig(data_path, "test-secret"))

    with TestClient(app) as client:
        response = client.get("/overview", headers={"X-Internal-Key": "test-secret"})
        assert client.get("/quality", headers={"X-Internal-Key": "test-secret"}).status_code == 200

    assert response.status_code == 200
    overview = response.json()["overview"]
    assert overview == {
        "jobs_created": 312,
        "completed_jobs": 281,
        "open_jobs": 31,
        "overdue_open_jobs": 26,
        "blocked_jobs": 9,
        "late_completed_jobs": 75,
        "completed_quantity": 86168,
        "good_quantity": 78555,
        "scrap_quantity": 7613,
        "aggregate_yield": "0.9116493361804846346671618234",
        "known_priced_work_at_risk": "590465.02",
        "priced_overdue_open_jobs": 10,
        "overdue_open_jobs_for_pricing": 26,
    }

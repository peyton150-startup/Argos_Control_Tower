# Argos Control Tower Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployable manufacturing control tower that deterministically converts the supplied event log into trusted factory state with operator-facing attention findings and source-event evidence.

**Architecture:** Polars performs the only production ingestion and normalization path, immutable Python dataclasses hold trusted domain state, and one projection builds `FactoryState` during FastAPI lifespan. A Next.js App Router frontend fetches that typed API only from Server Components and protects the operator workflow with Basic Auth in `proxy.ts`.

**Tech Stack:** Python 3.12+, uv, Polars, FastAPI, Pydantic v2, pytest, Ruff, DuckDB; Next.js App Router, React, TypeScript, Tailwind, pnpm, Vitest.

**Spec:** `00_BUILD_SPEC.md`, supported by `02_DATA_CONTRACT.md`, `01_IMPLEMENTATION_PLAN.md`, `03_CODEX_HANDOFF.md`, `04_PROJECT_PLAN.md`, and `05_SOURCE_NOTES.md`.

## Global Constraints

- Use `max(valid event timestamp)` as `factory_as_of`; never use wall-clock time for overdue state.
- Collapse exact duplicate copies, quarantine every record for a conflicting event ID, and preserve quarantined evidence.
- Treat `job_completed` as authoritative for completed, good, and scrap quantities.
- Treat missing price as unknown and label partial exposure “known priced work at risk,” including coverage.
- Keep manufacturing rules in ingestion/projection, never in FastAPI handlers or React.
- Build `FactoryState` once in FastAPI lifespan and return 200 from `/health` only when ready.
- Keep `INTERNAL_API_KEY`, `BASIC_AUTH_USER`, and `BASIC_AUTH_PASSWORD` server-side.
- Do not add databases, queues, workers, realtime infrastructure, AI, or speculative abstractions.
- Run local Python verification first; later, when requested, repeat it in Docker container `trellis-t19-test`.
- Reserve Docker container `trellis-ai-agent` for future PostgreSQL-specific testing only; PostgreSQL is not part of this MVP.

---

### Task 1: Repository Foundation

**Files:**
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `frontend/` using the official Next.js App Router scaffold
- Move: `manufacturing_events.jsonl` to `backend/data/manufacturing_events.jsonl`

**Interfaces:**
- Produces: Python package `app`; backend commands `uv run pytest` and `uv run ruff check .`; frontend commands `pnpm test`, `pnpm lint`, and `pnpm build`.

- [ ] **Step 1: Add root ignores and backend project metadata**

```toml
[project]
name = "argos-control-tower-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.116", "polars>=1.32", "pydantic>=2.11", "uvicorn[standard]>=0.35"]

[dependency-groups]
dev = ["duckdb>=1.3", "httpx>=0.28", "pytest>=8.4", "ruff>=0.12"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Scaffold the frontend**

Run:

```bash
pnpm create next-app frontend --ts --tailwind --eslint --app --src-dir --use-pnpm --import-alias "@/*" --yes
cd frontend && pnpm add -D vitest
```

Add `"test": "vitest run"` to `frontend/package.json`.

- [ ] **Step 3: Place the immutable dataset under the backend deploy root**

Run: `git mv manufacturing_events.jsonl backend/data/manufacturing_events.jsonl`

- [ ] **Step 4: Install and verify both projects**

Run: `cd backend && uv sync && uv run pytest && uv run ruff check .`

Expected: pytest reports no tests yet; Ruff passes.

Run: `cd frontend && pnpm test && pnpm lint && pnpm build`

Expected: Vitest reports no tests yet; lint and production build pass.

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend frontend
git commit -m "chore: initialize control tower"
```

---

### Task 2: Trusted Event Ingestion and Data Health

**Files:**
- Create: `backend/app/domain.py`
- Create: `backend/app/ingest.py`
- Create: `backend/tests/test_ingest.py`

**Interfaces:**
- Produces: `load_events(path: Path) -> IngestionResult`.
- Produces: `NormalizedEvent`, `DataHealth`, and `IngestionResult` frozen dataclasses.
- `IngestionResult.trusted_events` excludes conflicting IDs and retains one copy of exact duplicates; `quarantined_events` contains all conflicting records.

- [ ] **Step 1: Write failing tests for exact-copy collapse and conflicting-ID quarantine**

```python
def test_exact_duplicate_collapses_to_one(tmp_path: Path) -> None:
    result = load_events(write_jsonl(tmp_path, [CREATED, CREATED]))
    assert [event.event_id for event in result.trusted_events] == ["evt-1"]
    assert result.data_health.exact_duplicate_copies == 1

def test_conflicting_event_id_quarantines_every_copy(tmp_path: Path) -> None:
    conflict = {**CREATED, "quantity": 99}
    result = load_events(write_jsonl(tmp_path, [CREATED, conflict]))
    assert result.trusted_events == ()
    assert len(result.quarantined_events) == 2
    assert result.data_health.quarantined_event_ids == ("evt-1",)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `cd backend && uv run pytest tests/test_ingest.py -v`

Expected: collection fails because `app.ingest` and domain types do not exist.

- [ ] **Step 3: Implement immutable domain records and Polars ingestion**

```python
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
    metadata: Mapping[str, object]
    ingestion_index: int

def load_events(path: Path) -> IngestionResult:
    frame = pl.scan_ndjson(path, ignore_errors=False).with_row_index("ingestion_index").collect()
    # Convert rows strictly, group by event_id, compare canonical payloads excluding ingestion index,
    # retain one exact copy, quarantine all conflicting copies, and compute max trusted timestamp.
```

- [ ] **Step 4: Add failing dataset-baseline test**

```python
def test_supplied_dataset_ingestion_baseline() -> None:
    result = load_events(DATA_PATH)
    assert result.data_health.raw_rows == 19_519
    assert result.data_health.duplicate_event_ids == 19
    assert result.data_health.exact_duplicate_copies == 14
    assert result.data_health.conflicting_duplicate_ids == 5
    assert result.data_health.trusted_rows == 19_495
    assert result.factory_as_of.isoformat() == "2026-08-13T23:06:33+00:00"
```

- [ ] **Step 5: Run RED, implement remaining counters, then verify GREEN**

Run: `cd backend && uv run pytest tests/test_ingest.py -v`

Expected before implementation: baseline assertions fail. Expected after implementation: all ingestion tests pass.

- [ ] **Step 6: Run Ruff and commit**

```bash
cd backend && uv run ruff check .
git add backend/app/domain.py backend/app/ingest.py backend/tests/test_ingest.py
git commit -m "feat: ingest and validate manufacturing events"
```

---

### Task 3: Deterministic Factory Projection

**Files:**
- Modify: `backend/app/domain.py`
- Create: `backend/app/projection.py`
- Create: `backend/tests/test_projection.py`

**Interfaces:**
- Consumes: `IngestionResult.trusted_events`, `IngestionResult.data_health`, and `IngestionResult.factory_as_of`.
- Produces: `project_factory_state(result: IngestionResult) -> FactoryState`.
- Produces: `JobState`, `AttentionItem`, `QualityState`, `FactoryOverview`, and `FactoryState`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_overdue_uses_dataset_clock() -> None:
    state = project_factory_state(ingestion(created(due="2026-01-02"), as_of="2026-01-03"))
    assert state.overview.overdue_open_jobs == 1

def test_block_unblock_completion_transition() -> None:
    state = project_factory_state(ingestion(CREATED, BLOCKED, UNBLOCKED, BLOCKED_2, COMPLETED))
    job = state.jobs_by_id["job-1"]
    assert job.status == "completed"
    assert job.blocked is False
    assert job.current_block_reason is None
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && uv run pytest tests/test_projection.py -v`

Expected: failure because `project_factory_state` does not exist.

- [ ] **Step 3: Implement lifecycle replay and overview counts**

```python
def project_factory_state(result: IngestionResult) -> FactoryState:
    ordered = sorted(result.trusted_events, key=lambda event: (event.timestamp, event.ingestion_index))
    builders: dict[str, _JobBuilder] = {}
    for event in ordered:
        if event.job_id is not None:
            builders.setdefault(event.job_id, _JobBuilder(event.job_id)).apply(event)
    jobs = tuple(builder.freeze(result.factory_as_of) for builder in builders.values() if builder.created)
    return _freeze_factory_state(result, jobs, ordered)
```

- [ ] **Step 4: Write failing quantity, pricing, evidence, and order-independence tests**

```python
def test_completion_is_authoritative_for_quantities() -> None:
    state = project_factory_state(ingestion(CREATED, CYCLE_QTY_500, COMPLETED_QTY_10))
    assert state.overview.completed_quantity == 10
    assert state.overview.good_quantity == 9
    assert state.overview.scrap_quantity == 1

def test_projection_is_independent_of_input_order() -> None:
    forward = project_factory_state(ingestion(*EVENTS))
    reverse = project_factory_state(ingestion(*reversed(EVENTS)))
    assert forward == reverse
```

- [ ] **Step 5: Implement completion reconciliation, pricing coverage, attention, quality, and evidence**

Implement deterministic attention ordering as `(severity rank, overdue first, blocked first, due_at, entity_id)` and attach the lifecycle event IDs used for each finding. Aggregate quality only from trusted `inspection_failed` events and label counts as failed-inspection quantity.

- [ ] **Step 6: Add and satisfy supplied-dataset projection audit test**

```python
def test_supplied_dataset_projection_baseline() -> None:
    state = project_factory_state(load_events(DATA_PATH))
    assert state.overview.created_jobs == 312
    assert state.overview.completed_jobs == 281
    assert state.overview.open_jobs == 31
    assert state.overview.overdue_open_jobs == 26
    assert state.overview.blocked_jobs == 9
    assert state.overview.late_completed_jobs == 75
    assert state.overview.good_quantity == 78_555
    assert state.overview.scrap_quantity == 7_613
    assert state.overview.completed_quantity == 86_168
    assert state.overview.known_priced_work_at_risk == Decimal("590465.02")
    assert state.overview.priced_at_risk_jobs == 10
```

- [ ] **Step 7: Run the entire backend suite and Ruff, then commit**

```bash
cd backend && uv run pytest -v && uv run ruff check .
git add backend/app backend/tests
git commit -m "feat: project trusted factory state"
```

---

### Task 4: Independent DuckDB Audit

**Files:**
- Create: `backend/scripts/audit_dataset.py`
- Create: `backend/tests/test_audit.py`

**Interfaces:**
- Produces: `audit_dataset(path: Path) -> dict[str, int | str]` using DuckDB only as a development verifier.

- [ ] **Step 1: Write a failing audit-baseline test**

```python
def test_duckdb_audit_reproduces_raw_baselines() -> None:
    audit = audit_dataset(DATA_PATH)
    assert audit == {
        "raw_rows": 19_519,
        "distinct_event_ids": 19_500,
        "duplicate_event_ids": 19,
        "job_created_rows": 312,
        "factory_as_of": "2026-08-13 23:06:33+00:00",
    }
```

- [ ] **Step 2: Run RED, implement parameterized DuckDB queries, and verify GREEN**

Run: `cd backend && uv run pytest tests/test_audit.py -v`

The script must query NDJSON independently and must not import `app.projection`.

- [ ] **Step 3: Run backend verification and commit**

```bash
cd backend && uv run pytest -v && uv run ruff check .
git add backend/scripts backend/tests/test_audit.py
git commit -m "test: independently audit manufacturing dataset"
```

---

### Task 5: Typed FastAPI Read API

**Files:**
- Create: `backend/app/api_models.py`
- Create: `backend/app/api.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: one lifespan-built `FactoryState` stored at `app.state.factory_state`.
- Produces: `GET /health`, `/overview`, `/attention`, `/jobs`, `/jobs/{job_id}`, `/quality`, and `/machines`.
- Product endpoints require `X-Internal-Key`; `/health` remains public.

- [ ] **Step 1: Write failing readiness and authorization tests**

```python
def test_health_is_ready_after_lifespan(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ready"}

def test_product_endpoint_rejects_missing_key(client: TestClient) -> None:
    assert client.get("/overview").status_code == 401

def test_overview_returns_projected_state(client: TestClient) -> None:
    response = client.get("/overview", headers={"X-Internal-Key": "test-key"})
    assert response.status_code == 200
    assert response.json()["open_jobs"] == 31
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `cd backend && uv run pytest tests/test_api.py -v`

- [ ] **Step 3: Implement strict Pydantic response models and dependency-based key validation**

```python
class StrictResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

def require_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> None:
    if not secrets.compare_digest(x_internal_key or "", settings.internal_api_key):
        raise HTTPException(status_code=401, detail="Invalid internal API key")
```

- [ ] **Step 4: Implement lifespan and thin handlers**

Lifespan loads `DATA_PATH`, calls `load_events`, calls `project_factory_state`, stores the result once, and marks readiness. Handlers only select and serialize pieces of that state.

- [ ] **Step 5: Add 404, evidence-timeline, bad-key, and response-schema tests**

Run: `cd backend && uv run pytest tests/test_api.py -v`

Expected: all endpoint tests pass without rebuilding the projection per request.

- [ ] **Step 6: Run backend verification and commit**

```bash
cd backend && uv run pytest -v && uv run ruff check .
git add backend/app backend/tests/test_api.py
git commit -m "feat: expose control tower API"
```

---

### Task 6: Server-Side Frontend Boundary and Basic Auth

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/lib/auth.test.ts`
- Create: `frontend/proxy.ts`
- Create: `frontend/.env.example`

**Interfaces:**
- Produces: `getOverview()`, `getAttention()`, `getJobs()`, and `getJob(jobId)` server-only fetch helpers.
- Produces: `isAuthorized(request, credentials) -> boolean` used by `proxy.ts`.

- [ ] **Step 1: Write failing Basic Auth parser tests**

```typescript
it("accepts exactly matching credentials", () => {
  expect(isAuthorized(basicRequest("alex", "secret"), { user: "alex", password: "secret" })).toBe(true);
});

it("rejects malformed and mismatched credentials", () => {
  expect(isAuthorized(new Request("https://example.test"), CREDS)).toBe(false);
  expect(isAuthorized(basicRequest("alex", "wrong"), CREDS)).toBe(false);
});
```

- [ ] **Step 2: Run frontend tests and verify RED**

Run: `cd frontend && pnpm test`

- [ ] **Step 3: Implement auth helper, proxy, API types, and server-only fetcher**

```typescript
async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${requiredEnv("API_BASE_URL")}${path}`, {
    headers: { "X-Internal-Key": requiredEnv("INTERNAL_API_KEY") },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Argos API ${path} failed with ${response.status}`);
  return response.json() as Promise<T>;
}
```

- [ ] **Step 4: Verify tests, lint, and build; commit**

```bash
cd frontend && pnpm test && pnpm lint && pnpm build
git add frontend
git commit -m "feat: add authenticated operator shell"
```

---

### Task 7: Factory Snapshot and Needs Attention

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/components/factory-snapshot.tsx`
- Create: `frontend/src/components/attention-list.tsx`
- Create: `frontend/src/components/operator-dashboard.test.tsx`

**Interfaces:**
- Consumes: typed overview and attention responses.
- Produces: server-rendered operator home page with `as_of`, open/overdue/blocked state, yield, known-priced exposure with coverage, data health, and deterministic attention links.

- [ ] **Step 1: Write failing static-render behavior tests**

```typescript
it("labels partial pricing as known priced work at risk", () => {
  const html = renderToStaticMarkup(<FactorySnapshot overview={OVERVIEW} />);
  expect(html).toContain("Known priced work at risk");
  expect(html).toContain("10 of 26 overdue jobs priced");
  expect(html).not.toContain("Total revenue at risk");
});

it("links attention findings to affected jobs", () => {
  const html = renderToStaticMarkup(<AttentionList items={[BLOCKED_ITEM]} />);
  expect(html).toContain('/jobs/job_0001');
  expect(html).toContain("Supporting evidence");
});
```

- [ ] **Step 2: Run RED, implement the two views, and verify GREEN**

Run: `cd frontend && pnpm test`

- [ ] **Step 3: Compose the Server Component page and explicit backend-error state**

The page calls `Promise.all([getOverview(), getAttention()])`; manufacturing values are displayed but never recalculated in React.

- [ ] **Step 4: Run frontend verification and commit**

```bash
cd frontend && pnpm test && pnpm lint && pnpm build
git add frontend/src
git commit -m "feat: add factory snapshot and operator attention"
```

---

### Task 8: Job Investigation, Evidence, and Quality

**Files:**
- Create: `frontend/src/app/jobs/[jobId]/page.tsx`
- Create: `frontend/src/components/job-detail.tsx`
- Create: `frontend/src/components/event-timeline.tsx`
- Create: `frontend/src/components/quality-summary.tsx`
- Create: `frontend/src/app/quality/page.tsx`
- Create: `frontend/src/components/investigation.test.tsx`

**Interfaces:**
- Consumes: `JobDetailResponse` with ordered source events and `QualityResponse` with defect-code quantities.
- Produces: Snapshot → Attention → Job → Evidence navigation and a compact quality view.

- [ ] **Step 1: Write failing job/evidence and quality rendering tests**

```typescript
it("renders operational state and chronological event IDs", () => {
  const html = renderToStaticMarkup(<JobDetail job={JOB} />);
  expect(html).toContain("job_0001");
  expect(html.indexOf("evt_0001")).toBeLessThan(html.indexOf("evt_0002"));
});

it("describes resin_rich as a defect code", () => {
  const html = renderToStaticMarkup(<QualitySummary quality={QUALITY} />);
  expect(html).toContain("resin_rich");
  expect(html).not.toContain("resin percentage");
});
```

- [ ] **Step 2: Run RED, implement investigation components/pages, and verify GREEN**

Run: `cd frontend && pnpm test`

- [ ] **Step 3: Run frontend verification and commit**

```bash
cd frontend && pnpm test && pnpm lint && pnpm build
git add frontend/src
git commit -m "feat: add job evidence and quality insights"
```

---

### Task 9: Production Configuration, Audit, and README

**Files:**
- Create: `backend/railway.toml`
- Create: `backend/.env.example`
- Create: `frontend/vercel.json` only if required by the final Next.js scaffold
- Create: `README.md`
- Remove: `README_STARTER.md`

**Interfaces:**
- Produces: Railway start command and health check; documented Vercel/Railway environment contract; concise reviewer walkthrough.

- [ ] **Step 1: Add deploy configuration**

```toml
[deploy]
startCommand = "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 120
restartPolicyType = "ON_FAILURE"
```

- [ ] **Step 2: Write the short README**

Document what Argos is, the stack, dataset-clock/duplicate/completion/pricing decisions, local commands, environment variables, current limitations, and the reviewer flow. Do not duplicate the full planning documents.

- [ ] **Step 3: Run complete local verification**

```bash
cd backend && uv run pytest -v && uv run ruff check . && uv run python scripts/audit_dataset.py
cd frontend && pnpm test && pnpm lint && pnpm build
```

- [ ] **Step 4: Inspect repository and commit**

```bash
git status --short
git diff --check
git add README.md backend/railway.toml backend/.env.example frontend README_STARTER.md
git commit -m "docs: document stack and production decisions"
```

- [ ] **Step 5: Prepare—not merge—the pull request**

Verify the branch log and diff against `main`, push `codex/argos-control-tower`, and open a PR only after the user approves the final local result. Deployment remains a separate approval-gated external action because it requires Railway/Vercel credentials and changes external state.

- [ ] **Step 6: Run deferred container verification when requested**

Run the backend suite in `trellis-t19-test`. Use `trellis-ai-agent` only if PostgreSQL enters a separately approved future scope; do not add PostgreSQL merely to exercise that container.

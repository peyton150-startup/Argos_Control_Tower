# Argos Control Tower — Initial Build Spec

**Status:** implementation contract for the four-hour HELICON take-home  
**Repository:** `https://github.com/peyton150-startup/Argos_Control_Tower.git`  
**Input:** `manufacturing_events.jsonl`  
**Primary product thesis:** turn an imperfect manufacturing event stream into a trusted factory-state projection that tells an operator **what needs attention, why it matters, and what source events support the conclusion**.

---

## 1. Product outcome

Ship one focused operator workflow:

```text
RAW MANUFACTURING EVENTS
          ↓
TRUSTED FACTORY STATE
          ↓
FACTORY SNAPSHOT
          ↓
NEEDS ATTENTION
          ↓
JOB / QUALITY / MACHINE DETAIL
          ↓
SOURCE EVENT EVIDENCE
```

The product should feel like a small credible slice of HELICON's Argos operating system, not a generic BI dashboard.

### Must answer

1. What work is open?
2. What work is overdue?
3. What is currently blocked, and why?
4. What quality loss is occurring?
5. Which findings deserve operator attention first?
6. What underlying events justify each finding?

### Strong additions if time remains

1. Quality Pareto / drill-down.
2. Machine cycle-time comparison.
3. Data-health indicator.
4. Read-only "Ask Argos" explanation layer using Pydantic AI **only after the deterministic Control Tower is complete**.

---

## 2. Architecture

Use one repository and two deployable applications.

```text
Argos_Control_Tower/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── domain.py
│   │   ├── ingest.py
│   │   ├── projection.py
│   │   ├── api_models.py
│   │   └── api.py
│   ├── data/
│   │   └── manufacturing_events.jsonl
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
│
└── README.md
```

### Backend

- Python 3.12+
- Polars for production ingestion/transforms
- standard-library `dataclasses` for internal domain/projection objects
- Pydantic only for API contracts and optional Pydantic AI structured outputs
- FastAPI
- pytest
- Ruff
- DuckDB as an independent verification/audit tool, not a second runtime pipeline

### Frontend

- Next.js App Router
- TypeScript
- Tailwind
- Server Components by default
- Client Components only for actual interaction
- Recharts or another small chart library only if the quality/machine view earns it

### Deploy

- FastAPI → Railway (`/backend` root)
- Next.js → Vercel (`/frontend` root)

---

## 3. Hard architecture invariants

### A. One authoritative data path

```text
immutable JSONL
    ↓
Polars normalization / validation
    ↓
trusted events
    ↓
project_factory_state(...)
    ↓
FactoryState
    ↓
FastAPI response models
    ↓
Next.js
```

Do not recompute manufacturing rules in API handlers or React components.

### B. Historical dataset time is authoritative

```python
factory_as_of = max(valid_event.timestamp)
```

All overdue / days-late calculations use `factory_as_of`, never wall-clock `now()`.

### C. Raw evidence is preserved

Every important derived finding must include source `event_id` references or enough information to retrieve its supporting timeline.

### D. Conflicting duplicate event IDs never silently win

- exact duplicate payload → collapse duplicate copies
- same `event_id` with conflicting payload → quarantine the entire ambiguous ID from quantitative aggregates it can corrupt
- preserve both raw records for evidence/data-health reporting
- never "keep first" or "keep last"

### E. One definition per metric

Do not let multiple layers independently decide what "yield", "overdue", "blocked", or "completed quantity" means.

---

## 4. Domain modeling strategy

Use lightweight immutable-ish Python domain objects:

```python
@dataclass(frozen=True, slots=True)
class JobState:
    ...
```

Python dataclasses intentionally do **not** enforce type annotations at runtime; that is acceptable inside the deterministic projection because the ingestion layer normalizes the data and the projection is covered by focused tests.

Use Pydantic at the HTTP boundary:

```python
class JobResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    ...
```

This gives the UI a runtime-validated contract without paying Pydantic validation cost/ceremony for every internal object.

---

## 5. Core `FactoryState`

Conceptually:

```text
FactoryState
├── as_of
├── data_health
├── overview
├── jobs[]
├── attention_items[]
├── quality
└── machines[]
```

Keep the concrete type hierarchy small.

### `DataHealth`

Should include at least:

- raw row count
- exact duplicate copy count
- conflicting duplicate ID count
- trusted-event count
- validation/reconciliation issues

### `Overview`

Candidate fields:

- open jobs
- overdue open jobs
- currently blocked jobs
- uniquely completed jobs
- completed-job yield
- known priced work at risk
- price coverage for the at-risk set
- factory `as_of`

### `JobState`

Candidate fields:

- job_id
- customer_id
- part_id
- material
- facility
- priority
- target_quantity
- target_due_at
- created_at
- started_at
- completed_at
- current status
- blocked flag / current block reason
- good_quantity
- scrap_quantity
- completed_quantity
- yield
- unit_price_estimate
- known order value
- evidence event IDs

---

## 6. Authoritative metric rules

### Completion

`job_completed` is authoritative for final completed quantity.

Do **not** sum `cycle_completed.quantity` and call it finished output.

### Good / scrap

Use:

```text
job_completed.metadata.good_quantity
job_completed.metadata.scrap_quantity
```

Reconcile when applicable:

```text
good_quantity + scrap_quantity == job_completed.quantity
```

If reconciliation fails, report the inconsistency; do not silently repair it.

### Yield

For completed jobs:

```text
sum(good_quantity) / sum(job_completed.quantity)
```

Do not derive final yield from arbitrary sums of inspection events.

### Due date

Use:

```text
job_created.metadata.target_due_at
```

### Target quantity

Use:

```text
job_created.metadata.target_quantity
```

### Current blocked state

Replay valid `job_blocked` / `job_unblocked` transitions in deterministic event order.

A completion clears current blocked state.

Keep `job_hold` separate until its semantics are explicitly justified; do not silently equate it with `job_blocked`.

### Machine performance

Use:

```text
cycle_completed.metadata.cycle_time_seconds
```

Cycle events support process timing, not authoritative finished quantity.

Prefer comparisons within comparable part/tool groups if time permits; otherwise omit rather than present misleading raw averages.

### Pricing

`unit_price_estimate` is optional.

Use wording such as:

> Known priced work at risk

Also show pricing coverage (`priced jobs / affected jobs`) when displaying the figure.

Never call partial pricing "total revenue at risk."

---

## 7. Attention model

No opaque ML or LLM ranking.

Each `AttentionItem` must be deterministic and explainable.

Suggested categories:

1. blocked + overdue
2. blocked
3. overdue
4. quality risk
5. machine-performance risk
6. data-health warning

Candidate fields:

```text
id
severity
category
title
entity_type
entity_id
why_it_matters[]
supporting_facts[]
evidence_event_ids[]
```

If a priority order is needed, use a simple documented tuple/rule rather than a mysterious numeric score.

Example:

```text
severity class
→ overdue status
→ blocked status
→ business value if known
→ due-date age
```

Do not claim causal root cause unless the data explicitly supports it.

---

## 8. API contract

Use FastAPI lifespan to:

1. load the JSONL
2. validate / normalize
3. classify duplicates
4. build `FactoryState`
5. store the projection in application state

Do not rebuild the dataset on each HTTP request.

Recommended API:

```text
GET /health
GET /overview
GET /attention
GET /jobs
GET /jobs/{job_id}
GET /quality
GET /machines
```

### `/health`

Return HTTP 200 only after the data has loaded and `FactoryState` was built successfully.

Keep `/health` unauthenticated for Railway health checks.

### Product endpoints

Require:

```text
X-Internal-Key: <INTERNAL_API_KEY>
```

Use strict Pydantic response models to validate/filter outgoing data.

---

## 9. Frontend contract

Next.js App Router.

Use Server Components for:

- initial backend fetching
- secret-bearing Railway calls
- page composition

Use Client Components only for:

- filters
- sorting
- tabs
- charts
- row expansion
- small interactive controls

Do not add Redux, React Query, SWR, or similar unless an actual requirement appears.

### Basic Auth

Use Next.js `proxy.ts`.

Environment variables:

```text
BASIC_AUTH_USER
BASIC_AUTH_PASSWORD
```

Do not build accounts/sessions/Auth.js/Clerk.

### Backend connection

Vercel server code uses:

```text
API_BASE_URL
INTERNAL_API_KEY
```

The internal API key must never be exposed through `NEXT_PUBLIC_*`.

---

## 10. Must-ship UI

### A. Factory Snapshot

Show a compact "state as of" timestamp and the highest-value operational metrics.

### B. Needs Attention

This is the centerpiece.

It must answer at a glance:

- what is wrong
- why it matters
- severity
- affected job/machine/quality area
- key supporting facts

### C. Job Detail

Show operational/commercial state plus chronological evidence.

### D. Event Evidence

Every important finding must drill down to source events.

---

## 11. Strong additions

### Quality

Useful dimensions:

- defect code
- material
- part
- QC station
- customer
- completed yield / scrap

The dataset has a `resin_rich` defect code, but it does **not** provide continuous resin-percentage measurements. Do not imply otherwise.

### Machines

Cycle-time comparison only if it can be made defensible quickly.

---

## 12. Pydantic AI stretch gate

Pydantic AI is **not an MVP dependency**.

Do not install/build it until:

- core tests pass
- backend is deployed
- frontend is deployed
- Basic Auth works
- Factory Snapshot works
- Needs Attention works
- Job Detail/evidence works
- Quality is complete or consciously cut

If the gate is reached, the only approved AI feature is a read-only `Ask Argos`.

### `Ask Argos`

Give the agent deterministic tools that read `FactoryState`, e.g.:

```text
get_factory_overview()
get_attention_items()
get_job(job_id)
get_quality_summary()
get_machine(machine_id)
```

The LLM must not calculate authoritative metrics.

Structured output:

```text
InvestigationAnswer
├── summary
├── findings[]
├── evidence_event_ids[]
└── uncertainty
```

Use an output validator to reject nonexistent evidence IDs.

No mutation tools, memory system, RAG/vector DB, multi-agent workflow, or autonomous actions.

AI unit tests must use `TestModel` or `FunctionModel`, and real model requests must be disabled in tests.

---

## 13. Explicit non-goals

Do not build initially:

- PostgreSQL
- Supabase
- Redis / Upstash
- queues/workers
- realtime streaming
- websockets
- ML prediction
- causal modeling
- LLM-first analytics
- RAG/vector DB
- complex auth
- 3D digital twin
- extensive CI
- generic enterprise service/repository layers
- broad test suite

---

## 14. Definition of done

The take-home is shippable when:

- raw data loads deterministically
- data-health rules are applied
- focused projection tests pass
- FactoryState is built once at startup
- `/health` represents readiness
- deployed Railway API serves real projected data
- deployed Vercel UI is protected by Basic Auth
- Factory Snapshot works
- Needs Attention works
- Job Detail/evidence works
- important metrics are independently reconciled
- README is short and accurate
- Git history shows meaningful milestones

# Argos Control Tower

**Argos Control Tower turns manufacturing event data into an operational view of the factory, helping an operator understand what needs attention, why it matters, and what source events support the conclusion.**

Rather than asking someone to search through thousands of individual manufacturing events, Argos reconstructs the current factory state and organizes it around the next decision an operator may need to make.

The main workflow is:

```text
Factory Snapshot
      ↓
Needs Attention
      ↓
Job Detail
      ↓
Source Event Evidence
```

Argos is currently a **read-only decision-support system**. It helps surface and investigate operational conditions; it does not automatically change production state or make factory decisions.

---

## What Argos Helps an Operator Do

### See the factory at a glance

The **Factory Snapshot** provides a compact view of the current production state:

- open jobs
- overdue jobs
- currently blocked jobs
- completed production yield
- known priced work at risk
- pricing coverage for overdue work

For the supplied manufacturing dataset, Argos reconstructs:

```text
312 jobs
281 completed
31 open
26 open and overdue
9 currently blocked
75 completed late

86,168 completed units
78,555 good units
7,613 scrap units
91.16% aggregate completed-job yield
```

For overdue work where pricing information is available, Argos also identifies:

```text
$590,465.02 known priced work at risk
pricing available for 10 of 26 overdue open jobs
```

That distinction matters because price information is incomplete. Argos presents the amount as **known priced work at risk**, not total revenue at risk.

---

## Focus on What Needs Attention

The **Needs Attention** view is the main operational workflow.

Argos currently surfaces three deterministic conditions:

- **Blocked + Overdue**
- **Blocked**
- **Overdue**

Each finding identifies the affected job and can include:

- why the condition matters
- target due date
- block reason
- priority
- known estimated value
- supporting event IDs

The ordering comes from explicit projection rules rather than an opaque risk score.

This gives the operator a practical starting point: instead of looking at every job equally, begin with the work that currently has a clear operational exception.

---

## Investigate the Job

Selecting an attention item opens **Job Detail**.

The job view brings together the information needed to understand the condition in context:

### Identity and routing

- customer
- part
- material
- priority
- facility
- tool

### Current operational state

- blocked status
- overdue status
- completed-late status
- target due date
- target quantity
- active block reason
- time the active block began
- known estimated value when available

### Production facts

For completed work, Argos can also show:

- completed quantity
- good quantity
- scrap quantity
- yield

Missing information remains unknown rather than being displayed as a fabricated zero.

---

## Trace the Evidence

Every job includes its chronological manufacturing event timeline.

Attention findings retain references to the source events supporting the condition, so the investigation can move from:

```text
This job needs attention
        ↓
Why does it need attention?
        ↓
What happened to this job?
        ↓
Which source events show that?
```

This keeps the visual dashboard connected to the underlying manufacturing records instead of turning derived metrics into unexplained numbers.

---

## Understand Quality Conditions

The main Control Tower also contains a compact **Quality** view.

It summarizes trusted inspection events and the observed defect categories in the supplied data:

```text
voids           827
delamination    421
dimensional     347
surface         337
resin_rich      244
other           212
```

The interface also shows the inspection-event pass rate and passed / failed inspection-event counts.

These are event-level quality observations, not counts of unique defective parts.

Argos also avoids making claims the dataset cannot support. For example, `resin_rich` is an observed defect category; the source data does not contain a continuous resin-percentage measurement, so no resin-percentage or process-chemistry conclusion is inferred.

---

# How It Works

Argos follows one main data path:

```text
manufacturing_events.jsonl
        ↓
Polars ingestion + normalization
        ↓
trusted event stream
        ↓
deterministic FactoryState
        ↓
FastAPI + Pydantic
        ↓
Next.js server-side data layer
        ↓
operator interface
```

Each layer has a narrow responsibility.

```text
ingest.py
→ normalize source events and establish the trusted input

projection.py
→ reconstruct factory and business state

api.py
→ expose that state over HTTP

frontend/src/lib/data.ts
→ adapt API responses for the UI

components/
→ present the operator workflow
```

Manufacturing rules stay in the projection rather than being independently re-created in the API or React components.

---

## From Raw Events to Factory State

The source is a newline-delimited JSON event log with **19,519 raw records** covering activity such as:

```text
job_created
job_started
job_blocked
job_unblocked
job_completed

cycle_completed

inspection_passed
inspection_failed

tool_ready
maintenance_ping
shift_handoff
material_lot_scan
sensor_glitch
job_hold
```

Polars reads and normalizes the source data before the factory projection is created.

### Duplicate handling

The source contains both exact and conflicting duplicate event IDs.

Argos treats them differently:

```text
exact same event ID + same payload
→ keep one trusted copy
```

while:

```text
same event ID + conflicting payload
→ quarantine the ambiguous records
```

This avoids choosing an arbitrary version of a conflicting event while still preserving the original records for inspection.

---

## Deterministic Factory State

The backend converts trusted events into one `FactoryState`.

Conceptually:

```text
FactoryState
├── factory_as_of
├── data_health
├── overview
├── jobs
├── events_by_id
├── quality
└── attention
```

Events are replayed in a stable order using:

```text
timestamp
→ original ingestion position
```

The historical dataset also supplies its own factory clock:

```text
factory_as_of = 2026-08-13T23:06:33Z
```

Overdue and late calculations are therefore based on the time represented by the dataset rather than the computer's current date.

---

## One Source for Each Operational Fact

Different events own different pieces of factory state.

For example:

```text
job_created
→ customer
→ part
→ material
→ priority
→ facility
→ tool
→ target due date
→ target quantity
→ unit price estimate

job_started
→ production start

job_blocked / job_unblocked
→ active blocked state

job_completed
→ completed quantity
→ good quantity
→ scrap quantity
```

`job_completed` is authoritative for finished production quantities.

Cycle events remain useful process evidence, but their quantities are not summed and presented as final finished output.

When completed quantities reconcile, job yield can be calculated from:

```text
good quantity / completed quantity
```

The factory-level yield is then calculated from the trusted completed-job quantities.

---

# API

FastAPI exposes the projected state through a small read API:

```text
GET /health
GET /overview
GET /attention
GET /jobs
GET /jobs/{job_id}
GET /quality
```

The application loads the dataset and constructs `FactoryState` once during FastAPI startup rather than rebuilding the event history on every request.

Pydantic models define the HTTP response contracts between the Python backend and the frontend.

### Internal API access

Product endpoints require:

```text
X-Internal-Key
```

`/health` remains public so the backend can expose deployment readiness without exposing product data.

The API is intentionally read-only.

---

# Frontend

The operator interface uses:

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Server Components by default

Server-side data access is centralized in:

```text
frontend/src/lib/data.ts
```

The flow is:

```text
Next.js page
      ↓
data.ts
      ↓
FastAPI
      ↓
frontend view model
      ↓
React component
```

The FastAPI base URL and internal API key remain server-side.

API responses are converted into presentation-friendly values such as percentages, currency labels, attention cards, and job detail fields before reaching the visual components.

Current API requests use `cache: "no-store"` so the interface reflects the backend response at request time.

---

# Project Structure

```text
Argos_Control_Tower/
├── backend/
│   ├── app/
│   │   ├── domain.py
│   │   ├── ingest.py
│   │   ├── projection.py
│   │   ├── api_models.py
│   │   ├── api.py
│   │   └── main.py
│   ├── data/
│   │   └── manufacturing_events.jsonl
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/
│
└── README.md
```

---

# Stack

### Backend

- Python 3.12+
- Polars
- FastAPI
- Pydantic
- Uvicorn
- pytest
- Ruff

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Vitest
- ESLint

### Verification / development

- DuckDB for independent dataset checks
- GitHub Actions / deployment checks
- Railway backend deployment
- Vercel frontend deployment

DuckDB is used as an independent verification path rather than as a second production data pipeline.

---

# Running Locally

## Backend

Requirements:

- Python 3.12+
- `uv`

```bash
cd backend

uv sync
uv run pytest
uv run ruff check .
```

Set a local internal key:

```bash
INTERNAL_API_KEY=<your-local-secret>
```

Then run:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The default dataset is:

```text
backend/data/manufacturing_events.jsonl
```

`DATA_PATH` can optionally override that location.

Health:

```text
GET http://localhost:8000/health
```

Product requests require:

```text
X-Internal-Key: <your-local-secret>
```

---

## Frontend

Requirements:

- Node.js
- pnpm 11

```bash
cd frontend
pnpm install
```

Create:

```text
frontend/.env.local
```

with:

```text
API_BASE_URL=http://localhost:8000
INTERNAL_API_KEY=<the-same-local-secret>
```

Then:

```bash
pnpm dev
```

To run the frontend verification suite:

```bash
pnpm verify
```

which runs:

```text
Vitest
→ ESLint
→ Next.js production build
```

---

# Design Choices

The project intentionally keeps the critical path small.

For this fixed manufacturing event log, Argos does not require:

- a database
- Redis
- queues or workers
- WebSockets
- realtime infrastructure
- ML prediction
- a vector database
- autonomous AI actions
- a multi-agent system

Those technologies could become useful in a larger production environment, but they are not required to answer the core operational question this version of Argos is designed around.

The emphasis here is:

```text
understand the event stream
→ reconstruct factory state
→ surface important conditions
→ make them easy to investigate
→ preserve the evidence behind them
```

---

# What a Production Version Could Add

The current architecture leaves clear extension points for a live manufacturing environment.

Possible next steps include:

- persistent append-only event storage
- incremental factory-state updates
- streaming event ingestion
- alerting and escalation workflows
- filtering by facility, customer, material, or priority
- deeper defect investigation
- machine cycle-time comparison within comparable jobs
- richer equipment and quality integrations
- controlled operational actions

A future AI explanation layer could also read from the same trusted factory state, but the underlying operational metrics would remain deterministic rather than being calculated by the model.

---

# The Core Idea

Argos is designed to turn a large manufacturing event stream into a practical investigation workflow:

```text
What is happening?
        ↓
What needs attention?
        ↓
Why does it matter?
        ↓
What job is affected?
        ↓
What source events support that conclusion?
```

The result is a visual Control Tower that helps an operator move from factory-wide conditions to specific, evidence-backed issues and make a better-informed next move.

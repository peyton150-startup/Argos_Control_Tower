# Argos Control Tower — Four-Hour Implementation Plan

This plan optimizes for **correct factory-state reconstruction, a complete deployed workflow, and clear scope discipline**.

The 10-character timestamps are relative to the moment the official four-hour build starts.

---

## `T+00:00:00` → `T+00:10:00` — Foundation

### Goal

Get the repository into a clean two-app shape and make the first commit.

### Build

- create `/backend`
- create `/frontend`
- initialize Python project with `uv`
- initialize Next.js App Router with TypeScript/Tailwind/pnpm
- add root `.gitignore`
- place `manufacturing_events.jsonl` under `backend/data/`
- ensure data file inclusion is intentional and allowed for the take-home

### Dependencies

Backend minimum:

```text
polars
fastapi
uvicorn[standard]
pydantic
pytest
ruff
duckdb     # verification/dev path
```

Frontend minimum:

```text
next
react
react-dom
typescript
tailwind
```

Do not add chart/AI/database packages yet.

### Verify

- backend imports
- frontend dev server starts
- `git status` is understood

### Commit

```text
chore: initialize control tower
```

---

## `T+00:10:00` → `T+00:40:00` — Ingest + Data Health

### Goal

Turn the raw JSONL into a deterministic trusted event collection.

### Implement

1. `Polars.scan_ndjson(...)`
2. preserve original row position as a stable ingestion index
3. parse timestamps
4. classify duplicate event IDs:
   - exact duplicate copy
   - conflicting duplicate ID
5. exclude conflicting IDs from trusted quantitative data
6. retain raw conflicting records for evidence/data-health
7. compute `factory_as_of = max(valid timestamp)`
8. create compact `DataHealth`

### Important rules

- `ignore_errors=False`
- no silent coercion/repair of malformed values
- no `unique(event_id, keep="first")`
- do not make DuckDB part of the runtime pipeline

### Independent verification

Use a tiny DuckDB query/script to cross-check:

- raw row count
- distinct event IDs
- duplicate ID count
- job-created count
- max timestamp

### Baseline the implementation should reproduce

These are **audit targets, not constants to hard-code**:

```text
raw rows                         19,519
duplicate event IDs                  19
exact duplicate copies               14
conflicting duplicate IDs             5
factory_as_of             2026-08-13T23:06:33Z
```

If implementation results differ, investigate before continuing.

### Commit

```text
feat: ingest and validate manufacturing events
```

---

## `T+00:40:00` → `T+01:20:00` — Factory Projection

### Goal

Build the one authoritative `FactoryState`.

### Implement internal Python dataclasses

Keep models minimal:

```text
NormalizedEvent
DataHealth
JobState
AttentionItem
QualityState
MachineState
FactoryOverview
FactoryState
```

Prefer:

```python
@dataclass(frozen=True, slots=True)
```

where it does not complicate implementation.

### Implement

```text
project_factory_state(events) -> FactoryState
```

Projection must:

1. sort events deterministically
2. build job lifecycle/state
3. compute completed/open
4. derive overdue using dataset `as_of`
5. replay block/unblock transitions
6. use job completion facts for completed/good/scrap quantities
7. calculate aggregate completed-job yield
8. calculate known priced work at risk + price coverage
9. generate deterministic attention items
10. preserve evidence event IDs

### Baseline audit targets

Again: reproduce, do not hard-code.

```text
jobs created                         312
unique completed jobs                281
open jobs                             31
open + overdue jobs                   26
currently blocked jobs                 9
late completed jobs                   75
completed good quantity           78,555
completed scrap quantity            7,613
completed quantity                 86,168
aggregate completed-job yield      91.16%
known priced overdue-open work   $590,465.02
price coverage                    10 / 26 overdue-open jobs
```

### Minimum tests

1. projection is independent of input order
2. overdue uses dataset `as_of`
3. exact duplicate copies collapse
4. conflicting duplicate IDs do not silently affect aggregates
5. good + scrap reconciles to completion where expected
6. block → unblock → completion state is correct

### Cut line

If this phase is behind at `T+01:20:00`, cut machine normalization and any fancy attention scoring.

Do **not** cut projection correctness.

### Commit

```text
feat: project trusted factory state
test: cover factory state invariants
```

---

## `T+01:20:00` → `T+01:45:00` — FastAPI + Railway

### Goal

Expose the projection through a small typed read API and get production backend deployment alive early.

### Implement

FastAPI lifespan:

```text
startup
→ ingest
→ validate
→ project FactoryState
→ mark ready
```

Endpoints:

```text
GET /health
GET /overview
GET /attention
GET /jobs
GET /jobs/{job_id}
GET /quality
GET /machines
```

Pydantic API models:

- strict where appropriate
- `extra="forbid"` for derived API contracts
- do not use Pydantic to repair raw JSONL

Security:

```text
INTERNAL_API_KEY
```

Require `X-Internal-Key` on product endpoints.

Leave `/health` public.

### Deploy Railway

- service root: `/backend`
- configure `INTERNAL_API_KEY`
- configure health check `/health`
- generate public domain
- verify real `/overview` data from deployed service

### Cut line

If Railway is consuming excessive time, continue UI development against local FastAPI and use ngrok temporarily. Return to Railway during final deployment window.

### Commit

```text
feat: expose and deploy control tower API
```

---

## `T+01:45:00` → `T+02:10:00` — Next.js Foundation + Vercel

### Goal

Have the end-to-end production path alive before UI polish.

### Implement

- Next.js App Router
- server-side API helper
- Server Components fetch Railway
- `proxy.ts` HTTP Basic protection
- basic layout
- error state

Environment variables:

```text
API_BASE_URL
INTERNAL_API_KEY
BASIC_AUTH_USER
BASIC_AUTH_PASSWORD
```

No `NEXT_PUBLIC_` prefix for secrets.

### Deploy Vercel

- project root: `/frontend`
- configure production env vars
- deploy
- verify Basic Auth in incognito
- verify frontend successfully reads Railway data

### Commit

```text
feat: deploy authenticated operator shell
```

---

## `T+02:10:00` → `T+02:55:00` — Killer Workflow

### Goal

Build the part Alex should remember.

### 1. Factory Snapshot

Show:

- factory `as_of`
- open
- overdue
- blocked
- completed yield
- known priced work at risk + coverage
- data-health status

### 2. Needs Attention

Prioritize understandable deterministic findings.

Each row/card should expose:

```text
severity
category
entity/job
short reason
important facts
```

### 3. Job Detail

Show:

- customer
- part
- material
- priority
- target quantity
- due date
- current state
- block reason
- known value if present
- completion/yield if completed
- source timeline

### 4. Evidence

Ensure major findings have source `event_id`s.

### Definition of milestone success

Alex can go:

```text
Factory Snapshot
→ Needs Attention
→ Job
→ Evidence
```

on the deployed URL.

### Commit

```text
feat: add operator attention and job investigation
```

---

## `T+02:55:00` → `T+03:15:00` — Strong Addition Window

Order:

### 1. Quality

Prefer this first.

Build a compact defect view using:

```text
voids
delamination
dimensional
surface
resin_rich
other
```

Allow a few useful groupings only if cheap:

- material
- part
- QC station
- customer

### 2. Machine performance

Only if defensible quickly.

Prefer comparable part/tool baselines.

If not, cut it.

### 3. Pydantic AI

**Do not start unless the deterministic app is fully healthy and deployed.**

Realistically this is the first stretch to cut.

### Commit

```text
feat: add quality insights
```

---

# `T+03:15:00` — FEATURE FREEZE

No new product features after this point.

Allowed:

- bugs
- correctness fixes
- deployment fixes
- obvious accessibility/usability fixes
- README
- visual cleanup that cannot break behavior

---

## `T+03:15:00` → `T+03:35:00` — Reliability/Audit Pass

Run tests and Ruff.

Independently reconcile using DuckDB or a separate verification script:

```text
raw rows
duplicate IDs
exact duplicate copies
conflicting duplicate IDs
trusted rows
jobs created
unique completed
open
overdue open
current blocked
late completed
good quantity
scrap quantity
completed quantity
yield
known priced work at risk
pricing coverage
```

Inspect any disagreement.

Do not force the implementation to match an expected number without understanding why.

---

## `T+03:35:00` → `T+03:50:00` — Production Smoke Test

Incognito workflow:

```text
URL
→ Basic Auth
→ Factory Snapshot
→ Needs Attention
→ Job Detail
→ Evidence
→ Quality
→ refresh
→ deep link / reload
```

Also test:

```text
Railway /health
bad internal API key
frontend backend-error state
```

Verify secrets do not appear in browser-visible JS/network payloads.

---

## `T+03:50:00` → `T+04:00:00` — README + Submission

README only:

1. what it is
2. stack
3. key decisions
4. limitations / next steps

Review:

```text
git status
git log --oneline
production URL
Basic Auth password
repo visibility/access
```

Stop at four hours.

---

# Feature cut order

Cut first:

1. Pydantic AI / Ask Argos
2. machine-performance view
3. extra charts
4. advanced filters
5. extra styling

Never cut:

1. trusted projection
2. Needs Attention
3. evidence drill-down
4. production deployment
5. Basic Auth
6. short README

# Review checkpoints

The project gets two serious code reviews total. See `06_REVIEW_GATES.md`.

## Review Gate 1 — Factory Truth

Dispatch immediately after the FastAPI/backend milestone is complete and green, normally around `T+01:35`–`T+01:50`.

Freeze the exact SHA containing:

```text
ingest
+ duplicate policy
+ FactoryState
+ projection tests
+ Pydantic/FastAPI contracts
+ readiness
```

This review protects the semantic truth layer. While it runs, frontend shell/styling may continue against the frozen API contract, but do not change projection semantics until findings are resolved.

## Review Gate 2 — Exact Submission Readiness

Dispatch at feature freeze, approximately `T+03:15`, only after the intended submission is deployed end-to-end.

Freeze the exact submission-candidate SHA and review:

```text
correctness
+ UI claims
+ evidence traceability
+ Basic Auth
+ server/backend secret boundary
+ deployment/env configuration
+ smoke-test behavior
+ README accuracy
```

No new features after dispatch. Any later code change invalidates exact-SHA coverage and requires focused verification of the changed surface.

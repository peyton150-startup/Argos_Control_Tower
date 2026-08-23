# Codex / Sol Handoff — Argos Control Tower

## Your job

Implement the four-hour HELICON take-home in:

`https://github.com/peyton150-startup/Argos_Control_Tower.git`

Read these repo planning files before coding, in order:

1. `00_BUILD_SPEC.md`
2. `02_DATA_CONTRACT.md`
3. `01_IMPLEMENTATION_PLAN.md`
4. `04_PROJECT_PLAN.md`
5. `05_SOURCE_NOTES.md`

Treat them as the implementation contract.

---

# Primary objective

Build a small Argos-style manufacturing Control Tower that converts the supplied event log into **trusted operational state** and tells an operator:

> What requires attention right now, why does it matter, and what source events support the conclusion?

This is not a generic analytics dashboard.

This is not an AI-first application.

---

# Execution rules

## 1. Work milestone by milestone

For each milestone:

1. inspect current repo/code
2. state the smallest change required
3. implement
4. run focused tests/lint
5. repair failures
6. verify milestone acceptance criteria
7. commit the coherent milestone
8. continue

Do not batch the entire four-hour implementation into one giant unreviewed change.

## 2. Do not ask for architecture decisions already answered by the planning files

Prefer a reasonable implementation consistent with the contract.

If the contract leaves a genuine ambiguity:

```text
correct
> simple
> explainable
> deployed
> generalized
```

## 3. Do not add technology speculatively

Do not introduce:

```text
Postgres
Supabase
Redis
Upstash
queues
workers
ORMs
RAG
vector DB
ML
websockets
multi-agent AI
complex auth
```

unless a concrete blocking requirement appears.

Explain the blocking requirement before adding one.

## 4. Keep domain logic out of HTTP/UI layers

One authoritative pipeline:

```text
raw events
→ normalized trusted events
→ FactoryState
→ API
→ UI
```

API handlers expose `FactoryState`.

React renders API data.

Neither layer independently redefines manufacturing metrics.

---

# Backend implementation constraints

## Python internal domain

Prefer standard-library dataclasses for internal normalized/projection state.

Use `frozen=True, slots=True` where it stays simple.

Do not assume type hints perform runtime validation.

## Pydantic

Use Pydantic for:

- FastAPI request/response contracts
- strict derived-data boundary validation
- optional Pydantic AI structured outputs

Do not make every internal domain object a Pydantic model.

Do not make Pydantic responsible for "fixing" raw JSONL.

## Polars

Polars owns the production ingestion/transformation path.

Use lazy NDJSON scanning where practical.

Do not silently ignore parse errors.

## DuckDB

DuckDB is a development/audit verifier only.

It may independently reproduce counts but must not become a second production projection implementation.

---

# Critical data rules

## Dataset clock

```text
factory_as_of = max(valid event timestamp)
```

No wall-clock overdue calculations.

## Duplicates

Exact duplicate copies:

```text
collapse
```

Conflicting same-ID records:

```text
quarantine
preserve evidence
exclude from affected trusted aggregates
```

Never keep-first/keep-last.

## Completion

`job_completed` owns completed/good/scrap quantities.

Do not use cycle-event quantity as final output.

## Quality

Do not infer continuous resin percentage.

`resin_rich` is a defect code only.

## Pricing

Missing price is unknown, not zero.

Use "known priced work at risk" and expose coverage.

---

# Backend lifecycle

Use FastAPI lifespan.

Startup must:

```text
load data
→ normalize
→ validate
→ classify duplicates
→ project FactoryState
→ mark ready
```

`/health` returns 200 only after successful projection.

Do not rebuild FactoryState per request.

---

# Frontend implementation constraints

Use Next.js App Router.

Server Components own backend fetching by default.

Use Client Components only for actual interaction.

Keep Railway secret server-side.

Basic Auth belongs in `proxy.ts`.

Do not build a user system.

---

# MVP UI sequence

Build in this order:

1. Factory Snapshot
2. Needs Attention
3. Job Detail
4. Event Evidence
5. Quality
6. Machine performance only if still defensible/time-safe

A deployed working sequence from 1 → 4 beats five incomplete dashboard pages.

---

# Testing philosophy

Small, targeted suite.

Required projection tests:

1. input ordering does not change FactoryState
2. overdue uses dataset `as_of`
3. exact duplicate collapse
4. conflicting ID quarantine
5. completion reconciliation
6. block/unblock/completion state transition

Add regression tests when a bug is discovered.

Do not spend the take-home building broad generic test infrastructure.

---

# Pydantic AI gate

Do not install/build Pydantic AI during the MVP.

Only consider it after:

```text
backend deployed
frontend deployed
Basic Auth works
tests pass
Factory Snapshot works
Needs Attention works
Job Detail/evidence works
Quality complete or cut intentionally
```

If that gate is reached, first consult the current Pydantic AI docs.

Optional coding-agent helper:

```bash
npx skills add pydantic/skills
```

The only approved feature is read-only `Ask Argos`.

Its tools must read deterministic `FactoryState`; the model must not calculate authoritative metrics.

Use structured output plus evidence-ID validation.

Tests must use Pydantic AI `TestModel`/`FunctionModel` and block accidental real model requests.

---

# Feature freeze

At `T+03:15:00`, no new features.

Fix correctness/deploy issues and finish the submission.

---

# Commit expectations

Prefer a history roughly like:

```text
chore: initialize control tower
feat: ingest and validate manufacturing events
feat: project trusted factory state
test: cover factory state invariants
feat: expose and deploy control tower API
feat: deploy authenticated operator shell
feat: add operator attention and job investigation
feat: add quality insights
fix: harden production deployment
docs: document stack and decisions
```

Do not squash/rebase away the implementation history before submission.

---

# Stop conditions

If a sophisticated feature threatens the four-hour completion:

cut the feature.

Do not cut correctness of FactoryState, evidence, deployment, Basic Auth, or README.

At all times prefer:

```text
credible small Argos slice
```

over:

```text
large unfinished manufacturing platform
```

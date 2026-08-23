# Argos Control Tower — Project Plan

## 1. Delivery checklist

Required take-home deliverables:

- deployed URL
- Basic Auth password
- GitHub repository access + commit history
- very short README describing stack + decisions
- optional process artifacts

This planning set can serve as an optional process artifact if desired.

---

## 2. Provider plan

### Primary

```text
GitHub   → repository / commit history
Railway  → FastAPI backend
Vercel   → Next.js frontend
```

### Local

```text
Python 3.12+
uv
Polars
DuckDB
Node 20.9+
pnpm
Codex
```

### Fallback only

```text
ngrok → local FastAPI if Railway temporarily blocks frontend progress
```

### Keep off critical path

```text
Supabase
Upstash
Neon
Cloudflare
PostHog
Sentry/Axiom
```

They may be useful later, but the fixed 20k-event dataset does not justify adding them to the initial build.

---

## 3. Environment variables

### Railway backend

```text
INTERNAL_API_KEY=<generated-secret>
DATA_PATH=data/manufacturing_events.jsonl
```

`DATA_PATH` can default in code; only configure it if needed.

### Vercel frontend

```text
API_BASE_URL=https://<railway-domain>
INTERNAL_API_KEY=<same-generated-secret>
BASIC_AUTH_USER=alex
BASIC_AUTH_PASSWORD=<generated-password>
```

Never prefix secrets with `NEXT_PUBLIC_`.

---

## 4. Local commands — intended shape

### Backend

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
pnpm build
```

### Deploy

Railway from `/backend`.

Vercel project Root Directory `/frontend`.

---

## 5. Dependency budget

### Backend MVP

```text
polars
fastapi
uvicorn[standard]
pydantic
pytest
ruff
duckdb
```

Only add a library when an implemented feature needs it.

### Frontend MVP

```text
next
react
react-dom
typescript
tailwind
```

Optional after core flow:

```text
recharts
```

### AI stretch

Only after gate:

```text
pydantic-ai
```

---

## 6. Repo planning files

Recommended files in repo root before starting:

```text
00_BUILD_SPEC.md
01_IMPLEMENTATION_PLAN.md
02_DATA_CONTRACT.md
03_CODEX_HANDOFF.md
04_PROJECT_PLAN.md
05_SOURCE_NOTES.md
```

When the project is finished, the final `README.md` should stay short.

Do not turn the README into the implementation spec.

---

## 7. Workstream ownership

Even if Codex/Sol is used heavily:

### Human decision owner

- whether a derived metric is meaningful
- whether a product claim is defensible
- feature cuts
- deployment submission
- final walkthrough narrative

### Codex implementation owner

- scaffolding
- Polars ingestion
- dataclasses/projection
- focused tests
- FastAPI contracts
- Next.js components
- deployment config
- bug fixing

### Important

Do not let the coding agent redefine the product because it sees an easier dashboard to build.

The product thesis is locked unless the data proves a direct contradiction.

---

## 8. Scope board

### P0 — mandatory

- [ ] repository structure
- [ ] data ingestion
- [ ] duplicate policy
- [ ] FactoryState
- [ ] core projection tests
- [ ] FastAPI
- [ ] Railway deploy
- [ ] Vercel + Basic Auth
- [ ] Factory Snapshot
- [ ] Needs Attention
- [ ] Job Detail
- [ ] evidence timeline
- [ ] reliability reconciliation
- [ ] README
- [ ] submission smoke test

### P1 — strong

- [ ] Quality view
- [ ] data-health indicator
- [ ] simple filters

### P2 — only if ahead

- [ ] machine normalized cycle comparison
- [ ] richer charts
- [ ] Ask Argos / Pydantic AI

---

## 9. Reliability budget

Spend verification/research effort in this order:

```text
Ingest / data semantics    HIGH
Factory projection         VERY HIGH
API contract               MEDIUM
UI implementation          LOW-MEDIUM
Deployment                 HIGH at smoke-test time
Visual polish              LOW
```

A wrong yield/overdue/blocking claim is worse than an imperfect chart.

---

## 10. Walkthrough preparation

Be prepared to explain:

1. Why the dataset's own max timestamp is the factory clock.
2. Why conflicting duplicate IDs are quarantined instead of "deduped."
3. Why `job_completed` is authoritative for final quantities.
4. Why a database was intentionally omitted.
5. Why Python dataclasses are used internally and Pydantic at the boundary.
6. Why the operator UI is exception-oriented rather than chart-oriented.
7. What would change for a live Argos event stream:
   - persistent append-only event store
   - projection updates
   - streaming ingestion
   - alert/escalation workflows
   - richer equipment/quality integrations

---

## 11. Live-feature readiness

Keep clear extension seams:

```text
ingest.py       → source normalization
projection.py   → business state
api.py          → transport
frontend/lib    → API client
components      → views
```

Likely live feature requests should be cheap:

- filter by facility/customer/material
- compare defect categories
- add priority filter
- show only overdue
- add machine filter
- add a new deterministic attention rule

Avoid tightly coupling these to page-specific logic.

---

## 12. Submission freeze

At the end:

```text
git status --short
git log --oneline
backend health check
frontend incognito login
full operator workflow
README
```

Do not rewrite reviewed/visible history unless necessary.

Stop at the four-hour limit.

## 13. Review budget

Only two serious reviews are budgeted.

### Review 1 — Factory Truth

Target: after backend/API milestone, ~`T+01:35`–`T+01:50`.

Purpose: catch semantic errors before every screen inherits them.

### Review 2 — Exact Submission

Target: feature freeze, ~`T+03:15`.

Purpose: verify the exact deployed candidate across correctness, auth/secrets, integration, claims, and submission readiness.

See `06_REVIEW_GATES.md` for the exact contract.

Do not convert these into per-PR reviews. If PR numbering changes, preserve the semantic review boundaries.

# Argos Control Tower — Verified Source Notes

**Verified:** 2026-08-23  
**Purpose:** compact record of official documentation used to shape the initial implementation plan.

These sources justify architecture choices; they do not override evidence from the supplied manufacturing dataset.

---

## 1. Python — dataclasses

Official:

`https://docs.python.org/3/library/dataclasses.html`

Relevant guidance:

- `@dataclass` generates standard object methods from annotated fields.
- `frozen=True` emulates read-only instances.
- `slots=True` generates slots.
- dataclasses do **not** generally enforce the annotated field types at runtime.

Plan impact:

> Use standard Python dataclasses for lightweight internal normalized/projection state; do not expect them to perform runtime validation.

---

## 2. Polars — NDJSON scan

Official:

`https://docs.pola.rs/api/python/stable/reference/api/polars.scan_ndjson.html`

Relevant guidance:

- `scan_ndjson()` lazily reads newline-delimited JSON.
- returns a `LazyFrame`.
- enables optimizer projection/predicate pushdown.
- `ignore_errors=False` is the normal fail-visible behavior.
- schema/schema overrides are available.

Plan impact:

> Polars is the single production ingestion/transformation path.

---

## 3. DuckDB — JSON/NDJSON

Official:

`https://duckdb.org/docs/lts/data/json/loading_json`

and:

`https://duckdb.org/docs/current/clients/python/data_ingestion`

Relevant guidance:

- DuckDB directly reads JSON/NDJSON.
- `read_ndjson` is supported.
- parse errors are not ignored by default.
- DuckDB can directly query Polars DataFrames/LazyFrames.

Plan impact:

> DuckDB is an excellent independent audit/query tool, but it should not become a second production projection implementation.

---

## 4. Pydantic — strict validation

Official:

`https://docs.pydantic.dev/latest/concepts/strict_mode/`

Relevant guidance:

- Pydantic is coercive by default.
- strict mode rejects many implicit conversions.
- strictness can be configured per validation, field, or model.
- strict JSON validation can still have format-specific allowances.

Plan impact:

> Normalize raw JSONL explicitly in Polars; use strict Pydantic contracts mainly at derived/API boundaries where silent coercion would hide our own bug.

---

## 5. Pydantic AI — tools

Official:

`https://ai.pydantic.dev/tools/`

Relevant guidance:

- function tools can move logic out of the model.
- the docs explicitly call out using tools to make agent behavior more deterministic/reliable.

Plan impact:

> If `Ask Argos` is built, tools read the deterministic `FactoryState`; the LLM does not calculate authoritative manufacturing metrics.

---

## 6. Pydantic AI — structured output / validation / testing

Official:

`https://ai.pydantic.dev/output/`

`https://ai.pydantic.dev/testing/`

Relevant guidance:

- structured output types can be validated.
- `@agent.output_validator` supports domain/output validation.
- `TestModel` and `FunctionModel` avoid usage, latency, and variability in unit tests.
- `ALLOW_MODEL_REQUESTS=False` can block accidental real model calls.

Plan impact:

> Pydantic AI remains a stretch feature. If implemented, validate evidence IDs and test without real provider calls.

---

## 7. Pydantic AI — Codex coding skill

Official:

`https://ai.pydantic.dev/coding-agent-skills/`

Relevant command:

```bash
npx skills add pydantic/skills
```

The documentation states this works with Codex via the agentskills.io standard.

Plan impact:

> If Codex implements the stretch feature, install/read the current Pydantic skill first rather than relying on stale framework memory.

---

## 8. FastAPI — lifespan

Official:

`https://fastapi.tiangolo.com/advanced/events/`

Relevant guidance:

- lifespan is intended for startup/shutdown resources shared across requests.
- expensive/shared resources can be loaded before the app begins serving requests.

Plan impact:

> Load/normalize/project the fixed manufacturing dataset once during FastAPI lifespan, not per request.

---

## 9. FastAPI — response models

Official:

`https://fastapi.tiangolo.com/tutorial/response-model/`

Relevant guidance:

- response models validate returned data.
- they generate JSON Schema/OpenAPI contracts.
- they serialize and filter output to the declared shape.

Plan impact:

> Pydantic response models are valuable at the FastAPI boundary even though internal domain state remains standard Python dataclasses.

---

## 10. Next.js — Server and Client Components

Official:

`https://nextjs.org/learn/react-foundations/server-and-client-components`

Relevant guidance:

- App Router uses Server Components by default.
- data fetching/rendering on the server can reduce client code.
- interactive pieces can be isolated into Client Components.

Plan impact:

> Fetch Railway data server-side and keep the internal API key off the browser; use Client Components only for filters/charts/interactions.

---

## 11. Next.js environment baseline

Official:

`https://nextjs.org/learn/dashboard-app`

Relevant guidance:

- current App Router learning material lists Node.js 20.9+.
- GitHub + Vercel are part of the normal deployment workflow.

Plan impact:

> Verify Node 20.9+ before starting.

---

## 12. Railway — health checks

Official:

`https://docs.railway.com/deployments/healthchecks`

Plan impact:

> Use `/health` as a real readiness check that only returns 200 after the dataset is ingested and `FactoryState` exists.

---

## 13. Railway — monorepo

Official:

`https://docs.railway.com/deployments/monorepo`

Plan impact:

> Keep one GitHub repository/commit history while deploying `/backend` as its own Railway service.

---

## 14. Vercel — monorepo/root directory

Official Vercel deployment material:

`https://vercel.com/academy/production-monorepos/deploy-all-apps`

Relevant guidance:

- multiple apps in one repo can be independent Vercel projects.
- each project can use its own Root Directory and environment variables.

Plan impact:

> Deploy `/frontend` as the Vercel project root while retaining a single repository for Alex to inspect.

---

# High-level conclusions from the source pass

1. **Fewer runtime systems = more reliable within four hours.**
2. **Polars owns ingest; DuckDB audits.**
3. **Python dataclasses own internal state; Pydantic owns runtime API contracts.**
4. **FastAPI lifespan owns one-time factory projection initialization.**
5. **Next.js server-side fetching protects backend credentials and reduces client complexity.**
6. **Railway readiness should reflect real data readiness, not merely process startup.**
7. **Pydantic AI is only valuable after deterministic truth exists.**
8. **If AI is added, deterministic tools + structured output + offline model tests are the reliable path.**

# Review-gate rationale

The official stack guidance supports concentrating review effort at two architectural boundaries.

1. **Truth boundary:** Polars is the production NDJSON path and DuckDB is the independent audit path; the design intentionally creates one runtime source of derived truth. Review after this deterministic projection and its Pydantic/FastAPI boundary are complete.
2. **Delivery boundary:** FastAPI lifespan/readiness, Next.js server/client separation, Railway health checks, and Vercel environment/secrets behavior create the primary late-stage integration risk. Review the exact deployed submission SHA after these boundaries are wired together.

Therefore the project uses:

```text
Review 1 → trusted FactoryState + API contract
Review 2 → exact deployed submission candidate
```

Review gates are tied to exact commit SHAs rather than PR numbers because branch heads may move.

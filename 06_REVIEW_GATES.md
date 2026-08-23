# Argos Control Tower — Two-Review Strategy

The four-hour project has a maximum of **two serious code reviews**.

Do not review every PR. Review at the two boundaries where an undetected defect would have the highest blast radius.

---

## Review Gate 1 — Factory Truth

### Dispatch when

The following are all complete on one exact commit SHA:

- JSONL ingestion
- duplicate classification/quarantine
- deterministic `FactoryState`
- authoritative metric rules
- focused projection tests
- Pydantic/FastAPI response contracts
- `/health` readiness behavior
- backend lint/tests green

Recommended timing:

```text
approximately T+01:35 to T+01:50
```

This should normally happen after the backend/API milestone and before substantial UI logic is built.

### Freeze

Record:

```text
REVIEW_1_SHA=<exact commit>
```

Do not amend/rebase/squash that SHA while review is running.

### Reviewer focus

Review the complete chain:

```text
raw JSONL
→ normalization
→ duplicate policy
→ deterministic event ordering
→ FactoryState
→ API contract
```

Highest-risk questions:

1. Does `factory_as_of` come from the dataset rather than wall-clock time?
2. Can conflicting duplicate IDs silently affect trusted quantities?
3. Is `job_completed` authoritative for final/good/scrap quantities?
4. Does good + scrap reconcile where expected?
5. Are block/unblock/completion transitions deterministic?
6. Are open/overdue/completed states mutually coherent?
7. Is missing price treated as unknown rather than zero?
8. Are API models exposing projection state rather than recomputing it?
9. Does `/health` become ready only after successful projection?
10. Can source events be traced from important findings?

### While Review 1 runs

Codex may continue with **presentation-only frontend work** against the existing API contract:

- page shell
- layout
- styling
- components consuming existing response shapes

Codex must **not change projection semantics or API contracts** until Review 1 findings are resolved, unless a blocking implementation bug requires it.

### If Review 1 finds a material issue

Fix it.

Rerun the focused backend suite.

Record the new SHA.

The review is considered to cover the fixed SHA only if the reviewer explicitly verifies the fix; otherwise do a targeted verification of the finding rather than spending the second full-project review.

Do not consume Review 2 merely because Review 1 produced a small patch.

---

# Review Gate 2 — Exact Submission Readiness

### Dispatch when

The intended submission is feature-complete and deployed:

- Review 1 findings resolved
- Railway backend deployed
- Vercel frontend deployed
- Basic Auth works
- server-side frontend → backend authentication works
- Factory Snapshot works
- Needs Attention works
- Job Detail works
- source evidence works
- Quality complete or intentionally cut
- required tests/lint/build green
- production smoke test green
- README substantially final

Recommended timing:

```text
approximately T+03:15
```

This coincides with feature freeze.

### Freeze

Record:

```text
REVIEW_2_SHA=<exact submission candidate SHA>
```

Review the **exact SHA intended for submission**.

No feature work after dispatch.

### Reviewer focus

Review end-to-end submission risk:

1. Does deployed UI accurately represent `FactoryState`?
2. Are any displayed claims unsupported or misleading?
3. Does Needs Attention remain deterministic/explainable?
4. Can important claims drill back to evidence?
5. Are Basic Auth and internal API credentials correctly separated?
6. Are secrets absent from browser-visible `NEXT_PUBLIC_*`, JS bundles, and API responses?
7. Does Vercel call Railway server-side as intended?
8. Does Railway readiness reflect actual data readiness?
9. Do production environment variables match the deployed configuration?
10. Do refresh/deep links/error states work?
11. Do README claims match the code and deployed product?
12. Does the exact SHA have clean tests/lint/build and a sensible commit history?

### After Review 2

Only fix:

- BLOCKER / MAJOR correctness issues
- deployment failures
- auth/secrets problems
- misleading product claims
- obvious broken UX

Do not add features.

Any code change after Review 2 invalidates the exact-SHA review. If a change is unavoidable, run a focused verification of the changed surface and explicitly record that the reviewed SHA changed.

---

# Why these two gates

## Gate 1 protects truth

The stack deliberately centralizes manufacturing semantics in one deterministic projection. A defect here propagates to every API response and every UI screen, so reviewing after `FactoryState` + API contracts gives the highest early return.

## Gate 2 protects delivery

The late-stage risk is different:

```text
backend
+ API contract
+ server/client boundary
+ secrets
+ auth
+ deployment configuration
+ UI claims
```

Reviewing the exact submission candidate catches integration failures that a backend-only review cannot.

---

# PR / milestone mapping

The repository does not need a PR for every line of work. A likely progression is:

```text
PR / milestone 1
scaffold + ingest

PR / milestone 2
FactoryState + invariants

PR / milestone 3
FastAPI + Railway
        ↓
REVIEW 1 — FACTORY TRUTH

PR / milestone 4
Next.js + Vercel + Basic Auth

PR / milestone 5
Needs Attention + Job Evidence

PR / milestone 6
Quality / final product work
        ↓
FEATURE FREEZE
        ↓
REVIEW 2 — EXACT SUBMISSION SHA
```

If the implementation uses fewer or more PRs, preserve the **semantic gates**, not the PR numbers.

---

# Codex rule

Before continuing past either review gate, Codex must print a compact checkpoint:

```text
REVIEW GATE
SHA:
tests:
lint:
build:
deploy:
known limitations:
```

The gate is tied to the exact SHA, not merely to a branch name or PR number.

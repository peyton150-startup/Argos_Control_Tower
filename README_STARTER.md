# Argos Control Tower

A small manufacturing operations control tower built from a synthetic event stream. It reconstructs trusted factory state, prioritizes work that needs operator attention, and lets findings drill back to the source events that support them.

## Stack

- Python + Polars
- FastAPI + Pydantic API contracts
- Next.js + TypeScript + Tailwind
- Railway + Vercel

## Key decisions

- Raw manufacturing events remain the evidence/source of truth.
- Factory state is derived deterministically from one projection layer.
- Historical lateness uses the dataset's own final timestamp, not wall-clock time.
- Conflicting duplicate event IDs are quarantined rather than silently resolved.
- Final production/yield uses explicit completion facts rather than summed cycle quantities.
- The UI prioritizes operator exceptions over generic analytics.

## If I had more time

- live append-only event ingestion and incremental projections
- alert/escalation workflows
- deeper machine/process normalization

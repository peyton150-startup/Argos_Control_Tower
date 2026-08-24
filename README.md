# Argos Control Tower

Argos Control Tower turns raw manufacturing event data into a trusted operational view of the factory.

Instead of asking an operator to search through thousands of individual events, Argos answers three practical questions:

**What needs attention? Why does it matter? What evidence supports that conclusion?**

The result is a small decision-support system designed to help factory operators understand current conditions and make a better-informed next move.

---

## What Argos Helps an Operator Do

### See the factory at a glance

The Factory Snapshot summarizes the current trusted state of production, including:

- open and overdue jobs
- currently blocked work
- completed production yield
- known priced work at risk and pricing coverage

For the supplied manufacturing dataset, Argos reconstructs 312 jobs from 19,519 raw events and identifies 31 open jobs, 26 overdue jobs, and 9 currently blocked jobs.

### Focus on what needs attention

The **Needs Attention** view is the center of the product.

Argos deterministically surfaces conditions such as:

- blocked and overdue jobs
- blocked jobs
- overdue jobs

Each finding explains why it matters and links back to the job and source events behind the conclusion.

There is no opaque AI risk score deciding what the operator should trust.

### Investigate a job

Job Detail brings together the operational context needed to understand an issue:

- customer, part, material, facility, and priority
- due date and target quantity
- blocked state and block reason
- completed, good, and scrap quantities
- yield and known commercial value when available

From there, the operator can inspect the chronological event timeline that produced the state.

### Understand quality loss

The Quality view summarizes trusted inspection results and defect categories such as:

- voids
- delamination
- dimensional
- surface
- resin rich
- other

Argos reports only what the source data supports. For example, `resin_rich` is treated as a defect category—not as a measured resin percentage or causal process diagnosis.

---

## How It Works

Argos uses one authoritative data path:

```text
manufacturing_events.jsonl
        ↓
Polars ingestion + validation
        ↓
trusted event stream
        ↓
deterministic FactoryState
        ↓
FastAPI + strict Pydantic contracts
        ↓
Next.js operator interface

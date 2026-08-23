# Argos Control Tower — Data Contract & Baseline Audit

This file records what the supplied `manufacturing_events.jsonl` actually supports and the rules the application should use to convert that event stream into trusted factory state.

**Important:** baseline values below are test/audit targets discovered from the supplied file. Application code must calculate them; never hard-code them.

---

## 1. Raw shape

Observed top-level fields:

```text
event_id
timestamp
event_type
job_id
part_id
customer_id
machine_id
material
quantity
metadata
```

The dataset is newline-delimited JSON.

### Raw event count

```text
19,519
```

### Dataset clock

Latest valid event timestamp:

```text
2026-08-13T23:06:33Z
```

This timestamp is the Control Tower's `factory_as_of`.

---

## 2. Event vocabulary

Observed raw counts before duplicate handling:

```text
cycle_completed       12,965
inspection_passed      2,765
inspection_failed      2,388
job_created               312
tool_ready                302
job_started               302
job_completed             282
job_blocked                68
job_unblocked              59
shift_handoff              17
maintenance_ping           16
sensor_glitch              16
material_lot_scan          14
job_hold                   13
```

The raw `job_completed` count includes an exact duplicate copy for one completed job; there are 281 unique completed jobs after exact duplicate collapse.

---

## 3. Duplicate policy

Observed:

```text
duplicate event IDs        19
exact duplicate copies     14
conflicting duplicate IDs   5
```

Known conflicting IDs include:

```text
evt_005087
evt_009610
evt_009935
evt_014575
evt_014986
```

### Rule

#### Exact duplicate payload

Collapse to one trusted event.

#### Same event ID + conflicting payload

Quarantine the ambiguous ID.

Do not select first or last.

Preserve raw records for evidence and expose ambiguity through `DataHealth`.

Exclude ambiguous records from trusted quantitative aggregates they could corrupt.

---

## 4. Job creation facts

`job_created` establishes the main job contract.

Observed metadata may contain:

```text
priority
facility
target_due_at
target_quantity
tool_id
unit_price_estimate
```

`unit_price_estimate` is optional.

### Rules

```text
due date         = job_created.metadata.target_due_at
target quantity  = job_created.metadata.target_quantity
estimated value  = target_quantity * unit_price_estimate, only when price exists
```

---

## 5. Production facts

`job_started` indicates production start.

`cycle_completed` contains process/machine evidence including:

```text
machine_id
quantity
tool_id
cycle_time_seconds
```

### Critical rule

Do **not** sum `cycle_completed.quantity` and label it final output.

Cycle events in this dataset include adjacent records with the same cycle timing and differing quantities. Use cycle events for process timing/machine analysis.

---

## 6. Completion facts

`job_completed` is authoritative for finished production.

Observed metadata:

```text
good_quantity
scrap_quantity
```

### Rules

```text
completed quantity = job_completed.quantity
good quantity      = metadata.good_quantity
scrap quantity     = metadata.scrap_quantity
```

Reconcile:

```text
good + scrap == completed quantity
```

Dataset-wide trusted baseline:

```text
unique completed jobs         281
completed quantity         86,168
good quantity              78,555
scrap quantity              7,613
aggregate yield             91.16%
```

---

## 7. Open / overdue

After trusted duplicate handling:

```text
jobs created               312
unique completed jobs      281
open jobs                   31
open and overdue            26
late completed jobs         75
```

### Overdue rule

```text
open
AND target_due_at < factory_as_of
```

Do not compare historical jobs with wall-clock now.

---

## 8. Blocked state

Observed block reasons:

```text
missing_tool        28
material_wait       14
engineering_hold    10
awaiting_qc          9
machine_fault        7
```

Raw transition counts:

```text
job_blocked         68
job_unblocked       59
```

Trusted current blocked baseline:

```text
9 jobs
```

### Rule

Replay `job_blocked` / `job_unblocked` transitions in deterministic order.

A valid `job_completed` event clears current blocked state.

### `job_hold`

Treat `job_hold` as a separate observed event category.

Do not assume it is semantically identical to `job_blocked` without further evidence.

---

## 9. Quality

Inspection failure defect counts after trusted duplicate handling:

```text
voids           827
delamination    421
dimensional     347
surface         337
resin_rich      244
other           212
```

These counts describe failed inspection-event quantities/categories, not necessarily unique failed parts.

The dataset contains `resin_rich` as a defect code.

It does **not** provide a continuous "resin percentage" field.

Do not claim analysis of actual resin percentages.

---

## 10. Commercial exposure

Only some `job_created` events provide `unit_price_estimate`.

For the 26 open-and-overdue jobs, baseline pricing coverage is:

```text
10 / 26
```

Known priced work represented by those 10 jobs:

```text
$590,465.02
```

### UI wording

Correct:

```text
Known priced work at risk
Pricing available for 10 of 26 overdue open jobs
```

Incorrect:

```text
Total revenue at risk
```

---

## 11. Data health contract

Suggested structure:

```text
DataHealth
├── raw_rows
├── trusted_rows
├── exact_duplicate_copies
├── conflicting_duplicate_ids
├── quarantined_event_ids[]
├── validation_issue_count
└── reconciliation_issues[]
```

Data-health findings should not block the whole product unless they make the projection unsafe.

---

## 12. Deterministic event order

Recommended sort key:

```text
timestamp
then original ingestion row index
```

The row index exists only to make ties deterministic.

Do not invent causal order beyond what the file provides.

---

## 13. Evidence contract

Derived findings should carry source event IDs.

For example:

```text
AttentionItem
├── ...
└── evidence_event_ids[]
```

Job detail should allow the UI to show the relevant ordered timeline.

---

## 14. Audit expectations

Before submission, independently reproduce with DuckDB or a separate script:

```text
19,519 raw rows
19 duplicate event IDs
14 exact duplicate copies
5 conflicting duplicate IDs
312 jobs created
281 unique completed
31 open
26 open-and-overdue
9 currently blocked
75 completed late
78,555 good
7,613 scrap
86,168 completed
91.16% aggregate yield
$590,465.02 known priced overdue-open work
10 / 26 pricing coverage
```

A mismatch is a debugging signal, not a reason to hard-code these values.

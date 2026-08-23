import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getAttention, getJob, getOverview, getQuality } from "./data";

const overviewPayload = {
  factory_as_of: "2026-08-13T23:06:33Z",
  data_health: {},
  overview: {
    jobs_created: 312, completed_jobs: 281, open_jobs: 31, overdue_open_jobs: 26,
    blocked_jobs: 9, late_completed_jobs: 75, completed_quantity: 86168,
    good_quantity: 78555, scrap_quantity: 7613, aggregate_yield: "0.9116",
    known_priced_work_at_risk: "590465.02", priced_overdue_open_jobs: 10,
    overdue_open_jobs_for_pricing: 26,
  },
};

const attentionPayload = [
  {
    id: "attention:blocked_and_overdue:job_0220", severity: "high",
    category: "BLOCKED_AND_OVERDUE", title: "Blocked and overdue job",
    entity_type: "job", entity_id: "job_0220",
    why_it_matters: "The job has an active block and its target due time has passed.",
    supporting_facts: { priority: "normal", target_due_at: "2026-07-17T06:34:47Z", block_reason: "missing_tool", estimated_value: "5471.45" },
    evidence_event_ids: ["evt_000010", "evt_000155"],
  },
  {
    id: "attention:blocked_and_overdue:job_0242", severity: "high",
    category: "BLOCKED_AND_OVERDUE", title: "Blocked and overdue job",
    entity_type: "job", entity_id: "job_0242",
    why_it_matters: "The job has an active block and its target due time has passed.",
    supporting_facts: { priority: "normal", target_due_at: "2026-07-18T09:46:42Z", block_reason: "missing_tool" },
    evidence_event_ids: ["evt_000006", "evt_000653"],
  },
];

const jobPayload = {
  job_id: "job_0220", customer_id: "cust_northarc", part_id: "part_1010",
  material: "hybrid_weave_epoxy", priority: "normal", facility: "la_01", tool_id: "tool_02",
  target_due_at: "2026-07-17T06:34:47Z", created_at: "2026-07-04T08:57:08Z",
  started_at: "2026-07-07T08:38:46Z", completed_at: null, is_blocked: true,
  block_reason: "missing_tool", is_overdue: true, completed_late: false,
  estimated_value: "5471.45", target_quantity: 205, blocked_at: "2026-07-07T11:22:59Z",
  unit_price_estimate: "26.69", completed_quantity: null, good_quantity: null, scrap_quantity: null,
  yield_rate: null, created_event_id: "evt_000010", block_event_id: "evt_000155",
  completion_event_id: null,
  timeline: [
    { event_id: "evt_000010", timestamp: "2026-07-04T08:57:08Z", event_type: "job_created" },
    { event_id: "evt_000139", timestamp: "2026-07-07T08:38:46Z", event_type: "job_started" },
    { event_id: "evt_000155", timestamp: "2026-07-07T11:22:59Z", event_type: "job_blocked" },
  ],
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("frontend data adapter", () => {
  const originalBaseUrl = process.env.API_BASE_URL;
  const originalKey = process.env.INTERNAL_API_KEY;

  beforeEach(() => {
    process.env.API_BASE_URL = "http://api.internal/base/";
    process.env.INTERNAL_API_KEY = "test-secret";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    if (originalBaseUrl === undefined) delete process.env.API_BASE_URL;
    else process.env.API_BASE_URL = originalBaseUrl;
    if (originalKey === undefined) delete process.env.INTERNAL_API_KEY;
    else process.env.INTERNAL_API_KEY = originalKey;
  });

  it("requests the overview with server credentials and maps its display values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(overviewPayload));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getOverview()).resolves.toEqual({
      asOf: "2026-08-13T23:06:33Z", openJobs: 31, overdueJobs: 26, blockedJobs: 9,
      completedYieldLabel: "91.16%", knownPricedWorkAtRiskLabel: "$590,465.02",
      pricingCoverageLabel: "Pricing available for 10 of 26 overdue open jobs",
    });
    expect(fetchMock).toHaveBeenCalledWith("http://api.internal/base/overview", {
      cache: "no-store", headers: { "X-Internal-Key": "test-secret" },
    });
  });

  it("preserves API attention order and exact evidence IDs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(attentionPayload)));

    await expect(getAttention()).resolves.toEqual([
      {
        id: "attention:blocked_and_overdue:job_0220", jobId: "job_0220", category: "BLOCKED_AND_OVERDUE",
        title: "Blocked and overdue job", whyItMatters: "The job has an active block and its target due time has passed.",
        priority: "normal", targetDueAt: "2026-07-17T06:34:47Z", blockReason: "missing_tool",
        estimatedValueLabel: "$5,471.45", evidenceEventIds: ["evt_000010", "evt_000155"],
      },
      {
        id: "attention:blocked_and_overdue:job_0242", jobId: "job_0242", category: "BLOCKED_AND_OVERDUE",
        title: "Blocked and overdue job", whyItMatters: "The job has an active block and its target due time has passed.",
        priority: "normal", targetDueAt: "2026-07-18T09:46:42Z", blockReason: "missing_tool",
        estimatedValueLabel: null, evidenceEventIds: ["evt_000006", "evt_000653"],
      },
    ]);
  });

  it("maps quality totals and deterministically sorts defects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({
      inspection_passed_events: 2765, inspection_failed_events: 2388,
      inspection_event_pass_rate: "0.5366",
      defect_counts: { surface: 337, voids: 827, alpha: 827, resin_rich: 244 },
    })));

    await expect(getQuality()).resolves.toEqual({
      inspectionPassRateLabel: "53.66%", eventSummaryLabel: "2,765 passed / 2,388 failed inspection events",
      defects: [
        { code: "alpha", label: "Alpha", count: 827, relativeWidth: 100 },
        { code: "voids", label: "Voids", count: 827, relativeWidth: 100 },
        { code: "surface", label: "Surface", count: 337, relativeWidth: 41 },
        { code: "resin_rich", label: "Resin rich", count: 244, relativeWidth: 30 },
      ],
    });
  });

  it("maps job facts, timeline, and matching attention evidence", async () => {
    const fetchMock = vi.fn((url: string) => Promise.resolve(url.endsWith("/attention") ? json(attentionPayload) : json(jobPayload)));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getJob("job_0220")).resolves.toEqual({
      jobId: "job_0220", customerId: "cust_northarc", partId: "part_1010", material: "hybrid_weave_epoxy",
      status: "BLOCKED_AND_OVERDUE", createdAt: "2026-07-04T08:57:08Z", startedAt: "2026-07-07T08:38:46Z",
      completedAt: null, isBlocked: true, blockReason: "missing_tool", blockedAt: "2026-07-07T11:22:59Z",
      priority: "normal", facility: "la_01", toolId: "tool_02", targetDueAt: "2026-07-17T06:34:47Z",
      targetQuantity: 205, isOverdue: true, completedLate: false, completedQuantity: null, goodQuantity: null,
      scrapQuantity: null, yieldLabel: null, estimatedValueLabel: "$5,471.45",
      attentionEvidenceEventIds: ["evt_000010", "evt_000155"],
      evidence: [
        { eventId: "evt_000010", timestamp: "2026-07-04T08:57:08Z", eventType: "job_created" },
        { eventId: "evt_000139", timestamp: "2026-07-07T08:38:46Z", eventType: "job_started" },
        { eventId: "evt_000155", timestamp: "2026-07-07T11:22:59Z", eventType: "job_blocked" },
      ],
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://api.internal/base/jobs/job_0220", "http://api.internal/base/attention",
    ]);
  });

  it("returns null for a missing job without requesting attention", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ detail: "Job not found" }, 404));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getJob("missing")).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("throws clear errors for missing credentials and failed API responses", async () => {
    delete process.env.INTERNAL_API_KEY;
    await expect(getOverview()).rejects.toThrow("INTERNAL_API_KEY must be configured");

    process.env.INTERNAL_API_KEY = "test-secret";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail: "Nope" }, 500)));
    await expect(getQuality()).rejects.toThrow("FastAPI request to /quality failed with 500");
  });
});

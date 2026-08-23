import { describe, expect, it } from "vitest";

import { getAttention, getJob, getOverview, getQuality } from "./data";

describe("frontend data adapter", () => {
  it("returns the verified Projection-B overview display values", async () => {
    await expect(getOverview()).resolves.toEqual({
      asOf: "2026-08-13T23:06:33Z",
      openJobs: 31,
      overdueJobs: 26,
      blockedJobs: 9,
      completedYieldLabel: "91.16%",
      knownPricedWorkAtRiskLabel: "$590,465.02",
      pricingCoverageLabel:
        "Pricing available for 10 of 26 overdue open jobs",
    });
  });

  it("returns null for a job outside the fixture boundary", async () => {
    await expect(getJob("job_unknown")).resolves.toBeNull();
  });

  it("preserves Projection-C attention order and evidence", async () => {
    const items = await getAttention();

    expect(items.map(({ jobId, category }) => ({ jobId, category }))).toEqual([
      { jobId: "job_0220", category: "BLOCKED_AND_OVERDUE" },
      { jobId: "job_0242", category: "BLOCKED_AND_OVERDUE" },
      { jobId: "job_0191", category: "BLOCKED_AND_OVERDUE" },
    ]);
    expect(items[0]?.evidenceEventIds).toEqual(["evt_000010", "evt_000155"]);
  });

  it("returns trusted inspection-event quality values", async () => {
    const quality = await getQuality();

    expect(quality.inspectionPassRateLabel).toBe("53.66%");
    expect(quality.defects.map(({ code, count }) => ({ code, count }))).toEqual([
      { code: "voids", count: 827 },
      { code: "delamination", count: 421 },
      { code: "dimensional", count: 347 },
      { code: "surface", count: 337 },
      { code: "resin_rich", count: 244 },
      { code: "other", count: 212 },
    ]);
  });
});

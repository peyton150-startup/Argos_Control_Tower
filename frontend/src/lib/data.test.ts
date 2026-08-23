import { describe, expect, it } from "vitest";

import { getJob, getOverview } from "./data";

describe("frontend data adapter", () => {
  it("returns the verified Projection-A overview", async () => {
    await expect(getOverview()).resolves.toEqual({
      factoryAsOf: "2026-08-13T23:06:33Z",
      snapshot: {
        totalJobs: 312,
        openJobs: 31,
        completedJobs: 281,
        blockedJobs: 9,
      },
    });
  });

  it("returns null for a job outside the fixture boundary", async () => {
    await expect(getJob("job_unknown")).resolves.toBeNull();
  });
});

import type {
  BlockedAttentionView,
  JobDetailView,
  OverviewView,
} from "./types";

export const overviewFixture: OverviewView = {
  factoryAsOf: "2026-08-13T23:06:33Z",
  snapshot: {
    totalJobs: 312,
    openJobs: 31,
    completedJobs: 281,
    blockedJobs: 9,
  },
};

export const attentionFixture: BlockedAttentionView[] = [
  {
    jobId: "job_0152",
    customerId: "cust_helix",
    partId: "part_1016",
    material: "carbon_fiber_epoxy",
    blockReason: "engineering_hold",
    blockedAt: "2026-07-25T23:33:29Z",
  },
];

export const jobsFixture: Record<string, JobDetailView> = {
  job_0152: {
    jobId: "job_0152",
    customerId: "cust_helix",
    partId: "part_1016",
    material: "carbon_fiber_epoxy",
    status: "BLOCKED",
    createdAt: "2026-07-19T07:19:44Z",
    startedAt: "2026-07-25T20:14:00Z",
    completedAt: null,
    isBlocked: true,
    blockReason: "engineering_hold",
    blockedAt: "2026-07-25T23:33:29Z",
    evidence: [
      {
        eventId: "evt_004806",
        timestamp: "2026-07-19T07:19:44Z",
        eventType: "job_created",
      },
      {
        eventId: "evt_011404",
        timestamp: "2026-07-25T20:14:00Z",
        eventType: "job_started",
      },
      {
        eventId: "evt_011504",
        timestamp: "2026-07-25T23:33:29Z",
        eventType: "job_blocked",
      },
    ],
  },
  job_0276: {
    jobId: "job_0276",
    customerId: "cust_ember",
    partId: "part_1024",
    material: "carbon_fiber_pa6",
    status: "IN_PROGRESS",
    createdAt: "2026-07-09T17:27:11Z",
    startedAt: "2026-07-16T15:17:28Z",
    completedAt: null,
    isBlocked: false,
    blockReason: null,
    blockedAt: null,
    evidence: [
      {
        eventId: "evt_000433",
        timestamp: "2026-07-09T17:27:11Z",
        eventType: "job_created",
      },
      {
        eventId: "evt_003186",
        timestamp: "2026-07-16T15:17:28Z",
        eventType: "job_started",
      },
    ],
  },
  job_0257: {
    jobId: "job_0257",
    customerId: "cust_aeroform",
    partId: "part_1020",
    material: "phenolic_prepreg",
    status: "COMPLETED",
    createdAt: "2026-07-23T06:18:21Z",
    startedAt: "2026-07-26T19:30:19Z",
    completedAt: "2026-07-29T19:56:05Z",
    isBlocked: false,
    blockReason: null,
    blockedAt: null,
    evidence: [
      {
        eventId: "evt_008888",
        timestamp: "2026-07-23T06:18:21Z",
        eventType: "job_created",
      },
      {
        eventId: "evt_011972",
        timestamp: "2026-07-26T19:30:19Z",
        eventType: "job_started",
      },
      {
        eventId: "evt_015152",
        timestamp: "2026-07-29T19:56:05Z",
        eventType: "job_completed",
      },
    ],
  },
};

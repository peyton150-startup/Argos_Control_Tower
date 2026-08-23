export type JobStatus = "BLOCKED" | "IN_PROGRESS" | "COMPLETED";

export interface FactorySnapshotView {
  totalJobs: number;
  openJobs: number;
  completedJobs: number;
  blockedJobs: number;
}

export interface OverviewView {
  factoryAsOf: string;
  snapshot: FactorySnapshotView;
}

export interface BlockedAttentionView {
  jobId: string;
  customerId: string | null;
  partId: string | null;
  material: string | null;
  blockReason: string | null;
  blockedAt: string | null;
}

export interface EvidenceEventView {
  eventId: string;
  timestamp: string;
  eventType: string;
}

export interface JobDetailView {
  jobId: string;
  customerId: string | null;
  partId: string | null;
  material: string | null;
  status: JobStatus;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  isBlocked: boolean;
  blockReason: string | null;
  blockedAt: string | null;
  evidence: EvidenceEventView[];
}

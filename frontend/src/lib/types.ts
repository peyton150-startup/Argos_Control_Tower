export type JobStatus =
  | "BLOCKED_AND_OVERDUE"
  | "BLOCKED"
  | "OVERDUE"
  | "IN_PROGRESS"
  | "COMPLETED";

export interface OverviewView {
  asOf: string;
  openJobs: number;
  overdueJobs: number;
  blockedJobs: number;
  completedYieldLabel: string | null;
  knownPricedWorkAtRiskLabel: string;
  pricingCoverageLabel: string;
}

export type AttentionCategory =
  | "BLOCKED_AND_OVERDUE"
  | "BLOCKED"
  | "OVERDUE";

export interface AttentionView {
  id: string;
  jobId: string;
  category: AttentionCategory;
  title: string;
  whyItMatters: string;
  priority: string | null;
  targetDueAt: string | null;
  blockReason: string | null;
  estimatedValueLabel: string | null;
  evidenceEventIds: string[];
}

export interface QualityDefectView {
  code: string;
  label: string;
  count: number;
  relativeWidth: number;
}

export interface QualityView {
  inspectionPassRateLabel: string;
  eventSummaryLabel: string;
  defects: QualityDefectView[];
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
  priority: string | null;
  facility: string | null;
  toolId: string | null;
  targetDueAt: string | null;
  targetQuantity: number | null;
  isOverdue: boolean;
  completedLate: boolean;
  completedQuantity: number | null;
  goodQuantity: number | null;
  scrapQuantity: number | null;
  yieldLabel: string | null;
  estimatedValueLabel: string | null;
  attentionEvidenceEventIds: string[];
  evidence: EvidenceEventView[];
}

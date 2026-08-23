import type {
  AttentionCategory,
  AttentionView,
  JobDetailView,
  JobStatus,
  OverviewView,
  QualityView,
} from "./types";

if (typeof window !== "undefined") {
  throw new Error("The control tower data adapter is server-only");
}

type DecimalString = string;

interface ApiOverviewResponse {
  factory_as_of: string;
  overview: {
    open_jobs: number;
    overdue_open_jobs: number;
    blocked_jobs: number;
    aggregate_yield: DecimalString | null;
    known_priced_work_at_risk: DecimalString;
    priced_overdue_open_jobs: number;
    overdue_open_jobs_for_pricing: number;
  };
}

interface ApiAttentionResponse {
  id: string;
  category: AttentionCategory;
  title: string;
  entity_id: string;
  why_it_matters: string;
  supporting_facts: Record<string, string>;
  evidence_event_ids: string[];
}

interface ApiQualityResponse {
  inspection_passed_events: number;
  inspection_failed_events: number;
  inspection_event_pass_rate: DecimalString | null;
  defect_counts: Record<string, number>;
}

interface ApiJobDetailResponse {
  job_id: string;
  customer_id: string | null;
  part_id: string | null;
  material: string | null;
  priority: string | null;
  facility: string | null;
  tool_id: string | null;
  target_due_at: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  is_blocked: boolean;
  block_reason: string | null;
  is_overdue: boolean;
  completed_late: boolean;
  estimated_value: DecimalString | null;
  target_quantity: number | null;
  blocked_at: string | null;
  completed_quantity: number | null;
  good_quantity: number | null;
  scrap_quantity: number | null;
  yield_rate: DecimalString | null;
  timeline: Array<{
    event_id: string;
    timestamp: string;
    event_type: string;
  }>;
}

function config(): { baseUrl: string; apiKey: string } {
  const baseUrl = process.env.API_BASE_URL?.trim();
  const apiKey = process.env.INTERNAL_API_KEY?.trim();

  if (!baseUrl) throw new Error("API_BASE_URL must be configured");
  if (!apiKey) throw new Error("INTERNAL_API_KEY must be configured");

  return { baseUrl: baseUrl.replace(/\/+$/, ""), apiKey };
}

function apiUrl(path: string): string {
  const { baseUrl } = config();
  return `${baseUrl}/${path.replace(/^\/+/, "")}`;
}

async function request<T>(path: string): Promise<T> {
  const { apiKey } = config();
  let response: Response;

  try {
    response = await fetch(apiUrl(path), {
      cache: "no-store",
      headers: { "X-Internal-Key": apiKey },
    });
  } catch (error) {
    const detail = error instanceof Error ? `: ${error.message}` : "";
    throw new Error(`FastAPI request to ${path} could not be completed${detail}`);
  }

  if (!response.ok) {
    throw new Error(`FastAPI request to ${path} failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

function percentage(value: DecimalString | null): string | null {
  if (value === null) return null;
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function usd(value: DecimalString | null): string | null {
  if (value === null) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(value));
}

function defectLabel(code: string): string {
  return code.replace(/_/g, " ").replace(/^./, (letter) => letter.toUpperCase());
}

function jobStatus(job: ApiJobDetailResponse): JobStatus {
  if (job.is_blocked && job.is_overdue) return "BLOCKED_AND_OVERDUE";
  if (job.is_blocked) return "BLOCKED";
  if (job.is_overdue) return "OVERDUE";
  if (job.completed_at !== null) return "COMPLETED";
  return "IN_PROGRESS";
}

function mapAttention(item: ApiAttentionResponse): AttentionView {
  const facts = item.supporting_facts;
  return {
    id: item.id,
    jobId: item.entity_id,
    category: item.category,
    title: item.title,
    whyItMatters: item.why_it_matters,
    priority: facts.priority ?? null,
    targetDueAt: facts.target_due_at ?? null,
    blockReason: facts.block_reason ?? null,
    estimatedValueLabel: usd(facts.estimated_value ?? null),
    evidenceEventIds: item.evidence_event_ids,
  };
}

export async function getOverview(): Promise<OverviewView> {
  const response = await request<ApiOverviewResponse>("/overview");
  const overview = response.overview;
  return {
    asOf: response.factory_as_of,
    openJobs: overview.open_jobs,
    overdueJobs: overview.overdue_open_jobs,
    blockedJobs: overview.blocked_jobs,
    completedYieldLabel: percentage(overview.aggregate_yield),
    knownPricedWorkAtRiskLabel: usd(overview.known_priced_work_at_risk) ?? "$0.00",
    pricingCoverageLabel: `Pricing available for ${overview.priced_overdue_open_jobs} of ${overview.overdue_open_jobs_for_pricing} overdue open jobs`,
  };
}

export async function getAttention(): Promise<AttentionView[]> {
  const response = await request<ApiAttentionResponse[]>("/attention");
  return response.map(mapAttention);
}

export async function getQuality(): Promise<QualityView> {
  const quality = await request<ApiQualityResponse>("/quality");
  const maxCount = Math.max(0, ...Object.values(quality.defect_counts));
  const defects = Object.entries(quality.defect_counts)
    .sort(([leftCode, leftCount], [rightCode, rightCount]) =>
      rightCount - leftCount || leftCode.localeCompare(rightCode),
    )
    .map(([code, count]) => ({
      code,
      label: defectLabel(code),
      count,
      relativeWidth: maxCount === 0 ? 0 : Math.round((count / maxCount) * 100),
    }));

  return {
    inspectionPassRateLabel: percentage(quality.inspection_event_pass_rate) ?? "Unavailable",
    eventSummaryLabel: `${quality.inspection_passed_events.toLocaleString("en-US")} passed / ${quality.inspection_failed_events.toLocaleString("en-US")} failed inspection events`,
    defects,
  };
}

export async function getJob(jobId: string): Promise<JobDetailView | null> {
  const response = await requestOrNull<ApiJobDetailResponse>(`/jobs/${encodeURIComponent(jobId)}`);
  if (response === null) return null;

  const attention = await getAttention();
  const matchingAttention = attention.find((item) => item.jobId === response.job_id);
  return {
    jobId: response.job_id,
    customerId: response.customer_id,
    partId: response.part_id,
    material: response.material,
    status: jobStatus(response),
    createdAt: response.created_at,
    startedAt: response.started_at,
    completedAt: response.completed_at,
    isBlocked: response.is_blocked,
    blockReason: response.block_reason,
    blockedAt: response.blocked_at,
    priority: response.priority,
    facility: response.facility,
    toolId: response.tool_id,
    targetDueAt: response.target_due_at,
    targetQuantity: response.target_quantity,
    isOverdue: response.is_overdue,
    completedLate: response.completed_late,
    completedQuantity: response.completed_quantity,
    goodQuantity: response.good_quantity,
    scrapQuantity: response.scrap_quantity,
    yieldLabel: percentage(response.yield_rate),
    estimatedValueLabel: usd(response.estimated_value),
    attentionEvidenceEventIds: matchingAttention?.evidenceEventIds ?? [],
    evidence: response.timeline.map((event) => ({
      eventId: event.event_id,
      timestamp: event.timestamp,
      eventType: event.event_type,
    })),
  };
}

async function requestOrNull<T>(path: string): Promise<T | null> {
  const { apiKey } = config();
  let response: Response;

  try {
    response = await fetch(apiUrl(path), {
      cache: "no-store",
      headers: { "X-Internal-Key": apiKey },
    });
  } catch (error) {
    const detail = error instanceof Error ? `: ${error.message}` : "";
    throw new Error(`FastAPI request to ${path} could not be completed${detail}`);
  }

  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`FastAPI request to ${path} failed with ${response.status}`);
  return (await response.json()) as T;
}

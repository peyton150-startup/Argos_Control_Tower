import { Timestamp } from "@/components/timestamp";
import type { JobDetailView } from "@/lib/types";

interface JobDetailProps {
  job: JobDetailView;
}

const statusTreatment: Record<JobDetailView["status"], string> = {
  BLOCKED_AND_OVERDUE: "bg-alarm text-white",
  BLOCKED: "bg-alarm text-white",
  OVERDUE: "bg-safety text-graphite",
  IN_PROGRESS: "bg-safety text-graphite",
  COMPLETED: "bg-oxidized text-white",
};

export function JobDetail({ job }: JobDetailProps) {
  const hasCompletionFacts =
    job.completedQuantity !== null ||
    job.goodQuantity !== null ||
    job.scrapQuantity !== null ||
    job.yieldLabel !== null;

  return (
    <section aria-labelledby="job-detail-heading">
      <div className="grid gap-5 border border-steel bg-white p-5 shadow-panel sm:p-7 lg:grid-cols-[1fr_auto] lg:items-start">
        <div>
          <p className="eyebrow">Job record</p>
          <div className="mt-2 flex flex-wrap items-center gap-4">
            <h1
              id="job-detail-heading"
              className="font-mono text-3xl font-semibold tracking-[-0.05em] text-graphite sm:text-4xl"
            >
              {job.jobId}
            </h1>
            <span className={`status-badge ${statusTreatment[job.status]}`}>
              {job.status.replaceAll("_", " ")}
            </span>
          </div>
        </div>

        <dl className="grid grid-cols-3 divide-x divide-steel border-l-4 border-oxidized bg-panel">
          <div className="px-4 py-3">
            <dt className="detail-label">Blocked</dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-graphite">
              {job.isBlocked ? "YES" : "NO"}
            </dd>
          </div>
          <div className="px-4 py-3">
            <dt className="detail-label">Overdue</dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-graphite">
              {job.isOverdue ? "YES" : "NO"}
            </dd>
          </div>
          <div className="px-4 py-3">
            <dt className="detail-label">Late</dt>
            <dd className="mt-1 font-mono text-sm font-semibold text-graphite">
              {job.completedLate ? "YES" : "NO"}
            </dd>
          </div>
        </dl>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="border border-steel bg-white p-5 sm:p-6">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
            Identity & routing
          </h2>
          <dl className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            <div>
              <dt className="detail-label">Customer</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.customerId ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Part</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.partId ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Material</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.material ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Priority</dt>
              <dd className="mt-1 capitalize text-graphite">
                {job.priority ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Facility</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.facility ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Tool</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.toolId ?? "Unknown"}
              </dd>
            </div>
          </dl>
        </div>

        <div className="border border-steel bg-white p-5 sm:p-6">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
            Target & active block
          </h2>
          <dl className="mt-6 grid gap-5 sm:grid-cols-2">
            <div>
              <dt className="detail-label">Target due</dt>
              <dd className="mt-1 font-mono text-xs text-graphite">
                <Timestamp value={job.targetDueAt} emptyLabel="Unknown" />
              </dd>
            </div>
            <div>
              <dt className="detail-label">Target quantity</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.targetQuantity?.toLocaleString("en-US") ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Block reason</dt>
              <dd className="mt-1 capitalize text-graphite">
                {job.blockReason?.replaceAll("_", " ") ?? "None"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Blocked at</dt>
              <dd className="mt-1 font-mono text-xs text-graphite">
                <Timestamp value={job.blockedAt} emptyLabel="Not blocked" />
              </dd>
            </div>
            {job.estimatedValueLabel && (
              <div className="sm:col-span-2">
                <dt className="detail-label">Known estimated value</dt>
                <dd className="mt-1 font-mono text-lg font-semibold text-graphite">
                  {job.estimatedValueLabel}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <div className="mt-5 border border-steel bg-white p-5 sm:p-6">
        <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
          Lifecycle
        </h2>
        <dl className="mt-6 grid gap-5 sm:grid-cols-3">
          <div>
            <dt className="detail-label">Created</dt>
            <dd className="mt-1 font-mono text-xs text-graphite">
              <Timestamp value={job.createdAt} />
            </dd>
          </div>
          <div>
            <dt className="detail-label">Started</dt>
            <dd className="mt-1 font-mono text-xs text-graphite">
              <Timestamp value={job.startedAt} />
            </dd>
          </div>
          <div>
            <dt className="detail-label">Completed</dt>
            <dd className="mt-1 font-mono text-xs text-graphite">
              <Timestamp value={job.completedAt} />
            </dd>
          </div>
        </dl>
      </div>

      {hasCompletionFacts && (
        <div className="mt-5 border border-steel bg-white p-5 sm:p-6">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
            Completion facts
          </h2>
          <dl className="mt-6 grid grid-cols-2 gap-5 sm:grid-cols-4">
            <div>
              <dt className="detail-label">Completed</dt>
              <dd className="mt-1 font-mono text-lg text-graphite">
                {job.completedQuantity?.toLocaleString("en-US") ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Good</dt>
              <dd className="mt-1 font-mono text-lg text-graphite">
                {job.goodQuantity?.toLocaleString("en-US") ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Scrap</dt>
              <dd className="mt-1 font-mono text-lg text-graphite">
                {job.scrapQuantity?.toLocaleString("en-US") ?? "Unknown"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Yield</dt>
              <dd className="mt-1 font-mono text-lg text-graphite">
                {job.yieldLabel ?? "Unavailable"}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  );
}

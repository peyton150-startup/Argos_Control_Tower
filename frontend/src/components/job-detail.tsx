import { Timestamp } from "@/components/timestamp";
import type { JobDetailView } from "@/lib/types";

interface JobDetailProps {
  job: JobDetailView;
}

const statusTreatment: Record<JobDetailView["status"], string> = {
  BLOCKED: "bg-alarm text-white",
  IN_PROGRESS: "bg-safety text-graphite",
  COMPLETED: "bg-oxidized text-white",
};

export function JobDetail({ job }: JobDetailProps) {
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

        <div className="border-l-4 border-oxidized bg-panel px-4 py-3">
          <p className="detail-label">Currently blocked</p>
          <p className="mt-1 font-mono text-sm font-semibold text-graphite">
            {job.isBlocked ? "YES" : "NO"}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="border border-steel bg-white p-5 sm:p-6">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
            Identity
          </h2>
          <dl className="mt-6 grid gap-5 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <div>
              <dt className="detail-label">Customer</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.customerId ?? "Not recorded"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Part</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.partId ?? "Not recorded"}
              </dd>
            </div>
            <div>
              <dt className="detail-label">Material</dt>
              <dd className="mt-1 font-mono text-sm text-graphite">
                {job.material ?? "Not recorded"}
              </dd>
            </div>
          </dl>
        </div>

        <div className="border border-steel bg-white p-5 sm:p-6">
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
            Active block
          </h2>
          <dl className="mt-6 grid gap-5 sm:grid-cols-2">
            <div>
              <dt className="detail-label">Reason</dt>
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
    </section>
  );
}

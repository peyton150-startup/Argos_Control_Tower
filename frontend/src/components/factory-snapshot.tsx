import type { FactorySnapshotView } from "@/lib/types";

interface FactorySnapshotProps {
  snapshot: FactorySnapshotView;
}

const metrics: Array<{
  key: keyof FactorySnapshotView;
  label: string;
  treatment?: string;
}> = [
  { key: "totalJobs", label: "Total jobs" },
  { key: "openJobs", label: "Open jobs" },
  { key: "completedJobs", label: "Completed jobs" },
  {
    key: "blockedJobs",
    label: "Currently blocked",
    treatment: "border-alarm bg-alarm-soft",
  },
];

export function FactorySnapshot({ snapshot }: FactorySnapshotProps) {
  return (
    <section aria-labelledby="factory-snapshot-heading">
      <div className="mb-4 flex items-end justify-between gap-4 border-b border-steel pb-3">
        <div>
          <p className="eyebrow">Projection A</p>
          <h2 id="factory-snapshot-heading" className="section-title">
            Factory Snapshot
          </h2>
        </div>
        <p className="hidden max-w-sm text-right text-xs leading-5 text-steel-dark sm:block">
          Lifecycle totals supplied by the trusted factory projection.
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map(({ key, label, treatment = "border-steel bg-white" }) => (
          <div key={key} className={`metric-card ${treatment}`}>
            <dt className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-steel-dark">
              {label}
            </dt>
            <dd className="mt-7 text-4xl font-semibold tracking-[-0.06em] text-graphite sm:text-5xl">
              {snapshot[key].toLocaleString("en-US")}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

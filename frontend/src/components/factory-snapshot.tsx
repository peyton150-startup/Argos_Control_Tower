import type { OverviewView } from "@/lib/types";

interface FactorySnapshotProps {
  overview: OverviewView;
}

export function FactorySnapshot({ overview }: FactorySnapshotProps) {
  const metrics = [
    { label: "Open jobs", value: overview.openJobs.toLocaleString("en-US") },
    {
      label: "Overdue jobs",
      value: overview.overdueJobs.toLocaleString("en-US"),
      treatment: "border-safety bg-safety-soft",
    },
    {
      label: "Blocked jobs",
      value: overview.blockedJobs.toLocaleString("en-US"),
      treatment: "border-alarm bg-alarm-soft",
    },
    {
      label: "Completed yield",
      value: overview.completedYieldLabel ?? "Unavailable",
    },
  ];

  return (
    <section aria-labelledby="factory-snapshot-heading">
      <div className="mb-4 flex items-end justify-between gap-4 border-b border-steel pb-3">
        <div>
          <p className="eyebrow">Projection B</p>
          <h2 id="factory-snapshot-heading" className="section-title">
            Factory Snapshot
          </h2>
        </div>
        <p className="hidden max-w-sm text-right text-xs leading-5 text-steel-dark sm:block">
          Operational values supplied by the trusted factory projection.
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {metrics.map(
          ({ label, value, treatment = "border-steel bg-white" }) => (
            <div key={label} className={`metric-card ${treatment}`}>
              <dt className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-steel-dark">
                {label}
              </dt>
              <dd className="mt-7 text-4xl font-semibold tracking-[-0.06em] text-graphite sm:text-5xl">
                {value}
              </dd>
            </div>
          ),
        )}
      </dl>

      <div className="mt-3 grid gap-3 border border-steel bg-graphite p-5 text-paper shadow-panel sm:grid-cols-[1fr_auto] sm:items-end sm:p-6">
        <div>
          <p className="font-mono text-[0.63rem] uppercase tracking-[0.18em] text-steel">
            Known priced work at risk
          </p>
          <p className="mt-2 text-3xl font-semibold tracking-[-0.05em]">
            {overview.knownPricedWorkAtRiskLabel}
          </p>
        </div>
        <p className="max-w-md text-sm leading-6 text-steel">
          {overview.pricingCoverageLabel}
        </p>
      </div>
    </section>
  );
}

import type { QualityView } from "@/lib/types";

interface QualitySummaryProps {
  quality: QualityView;
}

export function QualitySummary({ quality }: QualitySummaryProps) {
  return (
    <section aria-labelledby="quality-heading">
      <div className="mb-4 border-b border-steel pb-3">
        <p className="eyebrow">Projection C</p>
        <h2 id="quality-heading" className="section-title">
          Quality
        </h2>
      </div>

      <div className="grid border border-steel bg-white shadow-panel lg:grid-cols-[18rem_1fr]">
        <div className="border-b border-steel bg-graphite p-6 text-paper lg:border-r lg:border-b-0">
          <p className="font-mono text-[0.63rem] uppercase tracking-[0.18em] text-steel">
            Inspection event pass rate
          </p>
          <p className="mt-6 text-5xl font-semibold tracking-[-0.06em]">
            {quality.inspectionPassRateLabel}
          </p>
          <p className="mt-4 text-xs leading-5 text-steel">
            {quality.eventSummaryLabel}
          </p>
        </div>

        <div className="p-5 sm:p-6">
          <div className="flex items-baseline justify-between gap-4">
            <h3 className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-oxidized">
              Failed inspection events by defect
            </h3>
            <span className="hidden text-xs text-steel-dark sm:inline">
              Event counts
            </span>
          </div>

          <ol className="mt-5 grid gap-4 sm:grid-cols-2">
            {quality.defects.map((defect) => (
              <li key={defect.code}>
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span>{defect.label}</span>
                  <span className="font-mono text-xs tabular-nums text-graphite">
                    {defect.count.toLocaleString("en-US")}
                  </span>
                </div>
                <div className="mt-2 h-1.5 bg-steel-light" aria-hidden="true">
                  <div
                    className="h-full bg-oxidized"
                    style={{ width: `${defect.relativeWidth}%` }}
                  />
                </div>
              </li>
            ))}
          </ol>

          <p className="mt-6 border-t border-steel-light pt-4 text-xs leading-5 text-steel-dark">
            Counts represent failed inspection events, not unique defective parts.
            Resin rich is a defect category; no resin percentage is inferred.
          </p>
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";

import { Timestamp } from "@/components/timestamp";
import type { AttentionCategory, AttentionView } from "@/lib/types";

interface NeedsAttentionProps {
  items: AttentionView[];
}

const categoryLabel: Record<AttentionCategory, string> = {
  BLOCKED_AND_OVERDUE: "Blocked + overdue",
  BLOCKED: "Blocked",
  OVERDUE: "Overdue",
};

export function NeedsAttention({ items }: NeedsAttentionProps) {
  return (
    <section aria-labelledby="needs-attention-heading">
      <div className="mb-4 border-b border-steel pb-3">
        <p className="eyebrow text-alarm">Projection C order</p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="needs-attention-heading" className="section-title">
            Needs Attention
          </h2>
          <p className="text-xs text-steel-dark">
            Showing {items.length} highest-ranked findings
          </p>
        </div>
      </div>

      <div className="grid gap-3">
        {items.map((item) => (
          <article
            key={item.id}
            className="grid border border-steel border-l-4 border-l-alarm bg-white shadow-panel md:grid-cols-[1fr_auto]"
          >
            <div className="p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-3">
                <span className="status-badge bg-alarm text-white">
                  {categoryLabel[item.category]}
                </span>
                <span className="font-mono text-base font-semibold text-graphite">
                  {item.jobId}
                </span>
              </div>

              <h3 className="mt-4 text-xl font-medium tracking-[-0.02em] text-graphite">
                {item.title}
              </h3>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-steel-dark">
                {item.whyItMatters}
              </p>

              <dl className="mt-5 grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                {item.targetDueAt && (
                  <div>
                    <dt className="detail-label">Target due</dt>
                    <dd className="mt-1 font-mono text-xs text-graphite">
                      <Timestamp value={item.targetDueAt} />
                    </dd>
                  </div>
                )}
                {item.blockReason && (
                  <div>
                    <dt className="detail-label">Block reason</dt>
                    <dd className="mt-1 capitalize text-graphite">
                      {item.blockReason.replaceAll("_", " ")}
                    </dd>
                  </div>
                )}
                {item.priority && (
                  <div>
                    <dt className="detail-label">Priority</dt>
                    <dd className="mt-1 capitalize text-graphite">
                      {item.priority}
                    </dd>
                  </div>
                )}
                {item.estimatedValueLabel && (
                  <div>
                    <dt className="detail-label">Known value</dt>
                    <dd className="mt-1 font-mono text-xs text-graphite">
                      {item.estimatedValueLabel}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            <Link
              href={`/jobs/${item.jobId}`}
              className="flex min-h-16 items-center justify-between gap-6 border-t border-steel bg-panel px-5 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-oxidized outline-none transition-colors hover:bg-steel-light focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-safety md:min-w-48 md:border-t-0 md:border-l"
            >
              View job
              <span aria-hidden="true">→</span>
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

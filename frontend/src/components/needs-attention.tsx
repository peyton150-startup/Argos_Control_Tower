import Link from "next/link";

import { Timestamp } from "@/components/timestamp";
import type { BlockedAttentionView } from "@/lib/types";

interface NeedsAttentionProps {
  items: BlockedAttentionView[];
  totalBlocked: number;
}

export function NeedsAttention({ items, totalBlocked }: NeedsAttentionProps) {
  return (
    <section aria-labelledby="needs-attention-heading">
      <div className="mb-4 border-b border-steel pb-3">
        <p className="eyebrow text-alarm">Current block state</p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 id="needs-attention-heading" className="section-title">
            Needs Attention
          </h2>
          <p className="text-xs text-steel-dark">
            Previewing {items.length} of {totalBlocked} currently blocked jobs
          </p>
        </div>
      </div>

      <div className="grid gap-3">
        {items.map((item) => (
          <article
            key={item.jobId}
            className="grid border border-steel border-l-4 border-l-alarm bg-white shadow-panel md:grid-cols-[1fr_auto]"
          >
            <div className="p-5 sm:p-6">
              <div className="flex flex-wrap items-center gap-3">
                <span className="status-badge bg-alarm text-white">Blocked</span>
                <span className="font-mono text-base font-semibold text-graphite">
                  {item.jobId}
                </span>
              </div>

              <p className="mt-4 text-xl font-medium tracking-[-0.02em] text-graphite">
                {item.blockReason?.replaceAll("_", " ") ?? "Reason not recorded"}
              </p>

              <dl className="mt-5 grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="detail-label">Blocked at</dt>
                  <dd className="mt-1 font-mono text-xs text-graphite">
                    <Timestamp value={item.blockedAt} />
                  </dd>
                </div>
                <div>
                  <dt className="detail-label">Customer</dt>
                  <dd className="mt-1 font-mono text-xs text-graphite">
                    {item.customerId ?? "Not recorded"}
                  </dd>
                </div>
                <div>
                  <dt className="detail-label">Part</dt>
                  <dd className="mt-1 font-mono text-xs text-graphite">
                    {item.partId ?? "Not recorded"}
                  </dd>
                </div>
                <div>
                  <dt className="detail-label">Material</dt>
                  <dd className="mt-1 font-mono text-xs text-graphite">
                    {item.material ?? "Not recorded"}
                  </dd>
                </div>
              </dl>
            </div>

            <Link
              href={`/jobs/${item.jobId}`}
              className="flex min-h-16 items-center justify-between gap-6 border-t border-steel bg-panel px-5 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-oxidized outline-none transition-colors hover:bg-steel-light focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-safety md:min-w-48 md:border-t-0 md:border-l"
            >
              Inspect job
              <span aria-hidden="true">→</span>
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

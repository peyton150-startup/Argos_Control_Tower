import Link from "next/link";
import { notFound } from "next/navigation";

import { ControlTowerHeader } from "@/components/control-tower-header";
import { EventTimeline } from "@/components/event-timeline";
import { JobDetail } from "@/components/job-detail";
import { getJob, getOverview } from "@/lib/data";

interface JobPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function JobPage({ params }: JobPageProps) {
  const { jobId } = await params;
  const [job, overview] = await Promise.all([getJob(jobId), getOverview()]);

  if (!job) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-paper">
      <ControlTowerHeader factoryAsOf={overview.asOf} />
      <main className="mx-auto max-w-7xl px-5 py-9 sm:px-8 sm:py-12 lg:px-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-oxidized outline-none hover:text-graphite focus-visible:ring-2 focus-visible:ring-safety"
        >
          <span aria-hidden="true">←</span>
          Factory snapshot
        </Link>

        <div className="mt-6">
          <JobDetail job={job} />
        </div>

        <div className="mt-12">
          <EventTimeline
            events={job.evidence}
            highlightedEventIds={job.attentionEvidenceEventIds}
          />
        </div>
      </main>
    </div>
  );
}

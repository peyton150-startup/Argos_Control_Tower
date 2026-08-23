import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center bg-paper px-5">
      <div className="w-full max-w-xl border border-steel bg-white p-8 shadow-panel sm:p-10">
        <p className="eyebrow text-alarm">Job not found</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-graphite">
          No fixture state exists for this job.
        </h1>
        <p className="mt-4 leading-7 text-steel-dark">
          This early shell includes only a small verified Projection-A sample.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex border border-oxidized bg-oxidized px-4 py-3 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-white outline-none hover:bg-graphite focus-visible:ring-2 focus-visible:ring-safety"
        >
          Return to factory snapshot
        </Link>
      </div>
    </main>
  );
}

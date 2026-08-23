import Link from "next/link";

interface ControlTowerHeaderProps {
  factoryAsOf: string;
}

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "2-digit",
  year: "numeric",
  timeZone: "UTC",
});

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

export function ControlTowerHeader({
  factoryAsOf,
}: ControlTowerHeaderProps) {
  const asOf = new Date(factoryAsOf);

  return (
    <header className="border-b-4 border-oxidized bg-graphite text-paper">
      <div className="mx-auto grid max-w-7xl gap-6 px-5 py-7 sm:px-8 lg:grid-cols-[1fr_auto] lg:items-stretch lg:px-10">
        <div className="flex items-center gap-4">
          <div
            aria-hidden="true"
            className="grid size-11 shrink-0 place-items-center border border-paper/30 bg-paper/5 font-mono text-sm font-semibold tracking-[0.18em]"
          >
            AC
          </div>
          <div>
            <Link
              href="/"
              className="inline-flex items-baseline gap-3 outline-none focus-visible:ring-2 focus-visible:ring-safety"
            >
              <span className="text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">
                Argos
              </span>
              <span className="font-mono text-[0.66rem] uppercase tracking-[0.28em] text-steel">
                Control Tower
              </span>
            </Link>
            <p className="mt-2 max-w-xl text-sm leading-6 text-steel">
              Trusted factory state for operator triage and evidence review.
            </p>
          </div>
        </div>

        <div className="factory-clock border-l border-paper/20 pl-5 font-mono lg:min-w-64">
          <div className="flex items-center gap-2 text-[0.62rem] uppercase tracking-[0.24em] text-steel">
            <span className="size-1.5 bg-safety" />
            Factory clock // UTC
          </div>
          <div className="mt-3 flex items-end justify-between gap-6">
            <span className="text-sm uppercase tracking-[0.12em]">
              {dateFormatter.format(asOf)}
            </span>
            <time
              dateTime={factoryAsOf}
              title={factoryAsOf}
              className="text-xl font-semibold tabular-nums text-white"
            >
              {timeFormatter.format(asOf)}
            </time>
          </div>
        </div>
      </div>
    </header>
  );
}

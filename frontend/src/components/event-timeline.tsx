import { Timestamp } from "@/components/timestamp";
import type { EvidenceEventView } from "@/lib/types";

interface EventTimelineProps {
  events: EvidenceEventView[];
  highlightedEventIds?: string[];
}

export function EventTimeline({
  events,
  highlightedEventIds = [],
}: EventTimelineProps) {
  const highlighted = new Set(highlightedEventIds);

  return (
    <section aria-labelledby="event-timeline-heading">
      <div className="border-b border-steel pb-3">
        <p className="eyebrow">Ordered evidence</p>
        <h2 id="event-timeline-heading" className="section-title">
          Event Timeline
        </h2>
      </div>

      <ol className="timeline-rail mt-6 space-y-1">
        {events.map((event) => {
          const isHighlighted = highlighted.has(event.eventId);

          return (
            <li
              key={event.eventId}
              className={`relative grid gap-3 border-b border-steel-light py-5 pr-3 pl-9 sm:grid-cols-[12rem_1fr_auto] sm:items-center sm:gap-6 ${isHighlighted ? "bg-alarm-soft" : ""}`}
            >
              <span
                aria-hidden="true"
                className={`absolute left-[0.3rem] top-7 size-3 border-2 border-paper ring-1 ${isHighlighted ? "bg-alarm ring-alarm" : "bg-oxidized ring-oxidized"}`}
              />
              <div className="font-mono text-xs tabular-nums text-steel-dark">
                <Timestamp value={event.timestamp} />
              </div>
              <div>
                <span className="font-medium capitalize text-graphite">
                  {event.eventType.replaceAll("_", " ")}
                </span>
                {isHighlighted && (
                  <span className="ml-3 font-mono text-[0.58rem] uppercase tracking-[0.14em] text-alarm">
                    Attention evidence
                  </span>
                )}
              </div>
              <code className="w-fit border border-steel bg-panel px-2 py-1 font-mono text-[0.68rem] text-oxidized">
                {event.eventId}
              </code>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

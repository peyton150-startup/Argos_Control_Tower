interface TimestampProps {
  value: string | null;
  emptyLabel?: string;
}

const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});

export function Timestamp({ value, emptyLabel = "Not recorded" }: TimestampProps) {
  if (!value) {
    return <span className="text-steel-dark">{emptyLabel}</span>;
  }

  return (
    <time dateTime={value} title={value}>
      {timestampFormatter.format(new Date(value))}
    </time>
  );
}

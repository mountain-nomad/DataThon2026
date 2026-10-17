import type { ViolationEvent } from "@/lib/types";

// Every figure is derived from the single event list, so a review mark updates them all.
export function ViolationStats({ events }: { events: ViolationEvent[] }) {
  const stats = [
    { label: "Total detected events", value: events.length },
    { label: "Cameras with detections", value: new Set(events.map((e) => e.cameraId).filter(Boolean)).size },
    { label: "Pending review", value: events.filter((e) => e.reviewStatus === "pending").length },
    { label: "False positives", value: events.filter((e) => e.reviewStatus === "false_positive").length },
  ];

  const byType = Object.entries(
    events.reduce<Record<string, number>>((acc, e) => ({ ...acc, [e.type]: (acc[e.type] ?? 0) + 1 }), {}),
  ).sort((a, b) => b[1] - a[1]);
  const max = byType[0]?.[1] ?? 0;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col gap-1 bg-surface p-5">
            <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{s.label}</dt>
            <dd className="text-3xl font-extrabold tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>

      {byType.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">By violation type</p>
          <ul className="flex flex-col gap-3">
            {byType.map(([type, count], i) => (
              <li key={type} className="flex flex-col gap-1">
                <div className="flex justify-between gap-4 text-sm">
                  <span>{type}</span>
                  <span className="tabular-nums text-muted">{count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-muted">
                  <div
                    className={`h-full rounded-full ${i === 0 ? "bg-primary" : "bg-muted/40"}`}
                    style={{ width: `${(count / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

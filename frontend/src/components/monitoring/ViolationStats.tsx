"use client";

import { useI18n } from "@/i18n/I18nProvider";
import { isScenarioId, SCENARIO_CODES, type AnalysisRecord } from "@/lib/types";

function Breakdown({ title, rows }: { title: string; rows: [string, number][] }) {
  const max = rows[0]?.[1] ?? 0;
  if (rows.length === 0) return null;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{title}</p>
      <ul className="flex flex-col gap-3">
        {rows.map(([label, count], i) => (
          <li key={label} className="flex flex-col gap-1">
            <div className="flex justify-between gap-4 text-sm">
              <span className="min-w-0 break-words">{label}</span>
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
  );
}

const countBy = (keys: string[]) =>
  Object.entries(keys.reduce<Record<string, number>>((acc, k) => ({ ...acc, [k]: (acc[k] ?? 0) + 1 }), {})).sort(
    (a, b) => b[1] - a[1],
  );

// Every figure is derived from the one list of finished analyses, so a review mark updates them all.
export function ViolationStats({ records }: { records: AnalysisRecord[] }) {
  const { t } = useI18n();
  const td = t.dashboard;
  const violations = records.flatMap((r) => r.results.filter((v) => v.status === "violation"));
  const stats = [
    { label: td.statVideos, value: records.length },
    { label: td.statFlaggedVideos, value: records.filter((r) => r.results.some((v) => v.status === "violation")).length },
    { label: td.statTotal, value: violations.length },
    { label: td.statPending, value: violations.filter((v) => v.reviewStatus === "pending").length },
    { label: td.statFalse, value: violations.filter((v) => v.reviewStatus === "false_positive").length },
  ];

  const scenarioName = (id: string | undefined) =>
    !id ? td.noScenario : isScenarioId(id) ? `${SCENARIO_CODES[id]} · ${t.scenarios[id].name}` : id;
  const byScenario = countBy(records.map((r) => scenarioName(r.scenario?.primary)));
  const byRule = countBy(violations.map((v) => v.ruleId ?? td.noRuleId));

  return (
    <div className="flex flex-col gap-8">
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border md:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col gap-1 bg-surface p-5 last:col-span-2 md:last:col-span-1">
            <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{s.label}</dt>
            <dd className="text-3xl font-extrabold tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>
      <div className="grid gap-8 md:grid-cols-2">
        <Breakdown title={td.byScenario} rows={byScenario} />
        <Breakdown title={td.byRule} rows={byRule} />
      </div>
    </div>
  );
}

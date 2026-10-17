"use client";

import { plural } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { formatTimecodePrecise } from "@/lib/format";
import { isScenarioId, SCENARIO_CODES, type PipelineResult, type SpecialistResult } from "@/lib/types";

// Results of the three AI stages, stacked and revealed one by one (frontend_description2.md §4).
// Everything shown comes from the pipeline response; only scenario names are translated.

const STATUS_DOT: Record<string, string> = {
  violation: "bg-forte-coral",
  no_violation: "bg-forte-sky",
};

function StageCard({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-3 rounded-2xl border border-border p-6 motion-safe:animate-reveal">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <span className="text-primary">{String(n).padStart(2, "0")}</span> · {title}
      </p>
      {children}
    </li>
  );
}

function Scenario({ id, secondary = false }: { id: string; secondary?: boolean }) {
  const { t } = useI18n();
  const known = isScenarioId(id);
  return (
    <div className="flex flex-col gap-0.5">
      {secondary && <p className="text-xs font-semibold text-muted">{t.inference.scenarioSecondary}</p>}
      <p className={`font-bold tracking-[0.02em] ${secondary ? "text-base" : "text-xl"}`}>
        {known ? SCENARIO_CODES[id] : id}
      </p>
      <p className="text-sm text-muted">{known ? t.scenarios[id].name : t.inference.scenarioOutside}</p>
    </div>
  );
}

function ResultItem({ result }: { result: SpecialistResult }) {
  const { t } = useI18n();
  const ti = t.inference;
  const status = ti.status[result.status as keyof typeof ti.status] ?? result.status;
  return (
    <li className="flex flex-col gap-3 border-t border-border pt-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold">
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className={`size-2 rounded-full ${STATUS_DOT[result.status] ?? "bg-muted"}`} />
          {status}
        </span>
        {result.ruleId && (
          <span className="text-muted">
            {ti.rule} <span className="font-mono text-foreground">{result.ruleId}</span>
          </span>
        )}
      </div>
      {result.evidence && (
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{ti.evidence}</p>
          <p className="text-sm">{result.evidence}</p>
        </div>
      )}
      {result.quote && (
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{ti.quote}</p>
          <blockquote className="border-l-2 border-border pl-3 text-sm text-muted">{result.quote}</blockquote>
        </div>
      )}
    </li>
  );
}

export function StageResults({
  shown,
  result,
  selectedId,
  onSelect,
}: {
  // How many stages are revealed (0–3).
  shown: number;
  result: PipelineResult | null;
  selectedId?: string;
  onSelect: (id: string) => void;
}) {
  const { locale, t } = useI18n();
  const ti = t.inference;
  if (shown === 0) return null;

  const scenario = result?.scenario ?? null;
  const results = result?.results ?? [];
  const violations = results.filter((r) => r.status === "violation");
  const others = results.filter((r) => r.status !== "violation");
  const verdict =
    violations.length > 0
      ? plural(locale, violations.length, ti.found)
      : results.length === 0
        ? ti.noResults
        : results.some((r) => r.status === "insufficient_evidence")
          ? ti.insufficient
          : ti.noViolation;
  const checked = [scenario?.primary, scenario?.secondary].filter((id): id is string => Boolean(id));

  return (
    <ol className="flex flex-col gap-4">
      <StageCard n={1} title={ti.stages.scenario}>
        {scenario ? (
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <Scenario id={scenario.primary} />
            {scenario.secondary && <Scenario id={scenario.secondary} secondary />}
          </div>
        ) : (
          <p className="text-sm text-muted">{ti.scenarioNone}</p>
        )}
      </StageCard>

      {shown >= 2 && (
        <StageCard n={2} title={ti.stages.violation}>
          <p className="text-xl font-bold">{verdict}</p>
          <p className="text-sm text-muted">{violations.length > 0 ? ti.flaggedNote : ti.noneNote}</p>
          {results.length > 0 && (
            <ul className="flex flex-col gap-4">
              {[...violations, ...others].map((r) => (
                <ResultItem key={r.id} result={r} />
              ))}
            </ul>
          )}
          {checked.map((id) =>
            isScenarioId(id) ? (
              <details key={id} className="border-t border-border pt-4 text-sm">
                <summary className="cursor-pointer font-semibold">
                  {ti.checksLabel}: {SCENARIO_CODES[id]}
                </summary>
                {t.scenarios[id].checks.length > 0 ? (
                  <ul className="mt-2 list-disc pl-5 text-muted">
                    {t.scenarios[id].checks.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-muted">{ti.noChecks}</p>
                )}
              </details>
            ) : null,
          )}
        </StageCard>
      )}

      {shown >= 3 && (
        <StageCard n={3} title={ti.stages.localization}>
          {violations.length === 0 ? (
            <p className="text-sm text-muted">{ti.nothingToLocalize}</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {violations.map((v) => {
                const active = v.id === selectedId;
                return (
                  <li key={v.id}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => onSelect(v.id)}
                      className={`flex flex-col items-start rounded-xl border px-4 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                        active ? "border-primary" : "border-border hover:bg-surface-muted"
                      }`}
                    >
                      <span className="text-xl font-bold tabular-nums">
                        {v.startSec === undefined
                          ? ti.notLocalized
                          : v.endSec !== undefined && v.endSec > v.startSec
                            ? `${formatTimecodePrecise(v.startSec)} – ${formatTimecodePrecise(v.endSec)}`
                            : formatTimecodePrecise(v.startSec)}
                      </span>
                      {v.ruleId && <span className="font-mono text-xs text-muted">{v.ruleId}</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </StageCard>
      )}
    </ol>
  );
}

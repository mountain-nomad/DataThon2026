"use client";

import { buttonSecondaryClass } from "@/components/Card";
import { EpisodeMedia } from "@/components/media/EpisodeMedia";
import { Field, ReviewBadge } from "@/components/media/EventDetails";
import { EvidenceFrames } from "@/components/media/EvidenceFrames";
import { fmt } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { formatDateTime, formatTimecodePrecise } from "@/lib/format";
import { isScenarioId, SCENARIO_CODES, type AnalysisRecord, type SpecialistResult } from "@/lib/types";

// One detected violation from an analysed video. Specialist text is shown untranslated.
export function EpisodeCard({
  record,
  result,
  busy,
  onToggleFalsePositive,
}: {
  record: AnalysisRecord;
  result: SpecialistResult;
  busy: boolean;
  onToggleFalsePositive: () => void;
}) {
  const { locale, t } = useI18n();
  const td = t.dashboard;
  const falsePositive = result.reviewStatus === "false_positive";
  const scenario = result.scenario ?? record.scenario?.primary;
  const { startSec, endSec } = result;

  return (
    <article
      id={`episode-${record.jobId}-${result.index}`}
      className={`grid scroll-mt-24 gap-6 rounded-2xl border border-border p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:p-6 ${
        falsePositive ? "bg-surface-muted" : "bg-surface"
      }`}
    >
      <EpisodeMedia
        result={result}
        src={record.previewUrl}
        label={fmt(td.episodeClip, { file: record.fileName || record.jobId })}
      />

      <div className="flex min-w-0 flex-col gap-4">
        <ReviewBadge status={result.reviewStatus} />
        <div className="flex flex-col gap-1">
          {scenario && (
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
              {isScenarioId(scenario) ? `${SCENARIO_CODES[scenario]} · ${t.scenarios[scenario].name}` : scenario}
            </p>
          )}
          <h3 className="break-words font-mono text-lg font-bold">{result.ruleId ?? td.noRuleId}</h3>
        </div>

        <dl className="grid gap-4 sm:grid-cols-3">
          <Field label={td.file}>
            <span className="break-all">{record.fileName || "—"}</span>
          </Field>
          <Field label={td.analysedAt}>{formatDateTime(record.createdAt, locale)}</Field>
          <Field label={td.time}>
            <span className="tabular-nums">
              {startSec === undefined
                ? "—"
                : endSec !== undefined && endSec > startSec
                  ? `${formatTimecodePrecise(startSec)} – ${formatTimecodePrecise(endSec)}`
                  : formatTimecodePrecise(startSec)}
            </span>
          </Field>
        </dl>

        <dl className="flex flex-col gap-4">
          {result.evidence && <Field label={td.evidence}>{result.evidence}</Field>}
          {result.quote && (
            <Field label={td.quote}>
              <blockquote className="border-l-2 border-border pl-3 text-muted">{result.quote}</blockquote>
            </Field>
          )}
          {result.evidenceFrames.length > 0 && (
            <Field label={td.frames}>
              <EvidenceFrames frames={result.evidenceFrames} />
            </Field>
          )}
        </dl>

        <button
          type="button"
          aria-pressed={falsePositive}
          disabled={busy}
          onClick={onToggleFalsePositive}
          className={`${buttonSecondaryClass} self-start disabled:opacity-50`}
        >
          {falsePositive ? td.undoFalse : td.markFalse}
        </button>
      </div>
    </article>
  );
}

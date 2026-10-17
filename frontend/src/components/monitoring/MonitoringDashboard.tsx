"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { buttonPrimaryLinkClass, buttonSecondaryClass, ErrorText } from "@/components/Card";
import { useI18n } from "@/i18n/I18nProvider";
import { api, toAnalysisRecord } from "@/lib/api";
import type { AnalysisRecord, ReviewStatus } from "@/lib/types";
import { EpisodeCard } from "./EpisodeCard";
import { ViolationStats } from "./ViolationStats";

function SectionTitle({ n, title, children }: { n: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="flex items-baseline gap-3 text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <span className="text-primary tabular-nums">{n}</span>
        {title}
      </p>
      {children && <p className="text-sm text-muted">{children}</p>}
    </div>
  );
}

const key = (jobId: string, index: number) => `${jobId}:${index}`;

// Statistics and episodes over the finished analyses from GET /api/jobs: the videos uploaded on
// /demo-inference. Nothing here is precomputed or invented; with no backend, the page says so.
export function MonitoringDashboard() {
  const { t, href } = useI18n();
  const td = t.dashboard;
  const [records, setRecords] = useState<AnalysisRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string[]>([]);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const { items } = await api.jobs(signal);
      setRecords(items.map(toAnalysisRecord));
    } catch (e) {
      if (signal?.aborted) return;
      setError(e instanceof Error ? e.message : String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const run = new AbortController();
    load(run.signal);
    return () => run.abort();
  }, [load]);

  const setReview = (jobId: string, index: number, reviewStatus: ReviewStatus) =>
    setRecords((list) =>
      list?.map((r) =>
        r.jobId !== jobId
          ? r
          : { ...r, results: r.results.map((v) => (v.index === index ? { ...v, reviewStatus } : v)) },
      ) ?? null,
    );

  // Human review is stored apart from the model output. The mark shows at once and is rolled
  // back if the backend doesn't accept it.
  async function toggleFalsePositive(jobId: string, index: number, current: ReviewStatus | undefined) {
    const next: ReviewStatus = current === "false_positive" ? "pending" : "false_positive";
    const k = key(jobId, index);
    setReviewError(null);
    setSaving((s) => [...s, k]);
    setReview(jobId, index, next);
    try {
      await api.review(jobId, index, next);
    } catch (e) {
      setReview(jobId, index, current ?? "pending");
      setReviewError(e instanceof Error ? e.message : String(e));
    }
    setSaving((s) => s.filter((x) => x !== k));
  }

  const episodes = (records ?? []).flatMap((record) =>
    record.results.filter((r) => r.status === "violation").map((result) => ({ record, result })),
  );

  return (
    <div className="flex flex-col gap-16">
      <section className="flex flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionTitle n="01" title={td.stats} />
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className={`${buttonSecondaryClass} disabled:opacity-50`}
          >
            {td.refresh}
          </button>
        </div>

        {error ? (
          <ErrorText error={`${td.loadError}${error}`} prefix={td.errorPrefix} />
        ) : records === null ? (
          <p aria-live="polite" className="text-sm text-muted">
            {td.loading}
          </p>
        ) : records.length === 0 ? (
          <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border px-6 py-10 text-center">
            <p className="max-w-md text-sm text-muted">{td.empty}</p>
            <Link href={href("/demo-inference")} className={buttonPrimaryLinkClass}>
              {td.toInference}
            </Link>
          </div>
        ) : (
          <ViolationStats records={records} />
        )}
      </section>

      {records !== null && records.length > 0 && (
        <section className="flex flex-col gap-6">
          <SectionTitle n="02" title={td.episodes}>
            {td.episodesNote}
          </SectionTitle>
          <ErrorText error={reviewError} prefix={td.reviewError} />
          {episodes.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-border px-6 py-10 text-center text-sm text-muted">
              {td.noEpisodes}
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              {episodes.map(({ record, result }) => (
                <EpisodeCard
                  key={key(record.jobId, result.index)}
                  record={record}
                  result={result}
                  busy={saving.includes(key(record.jobId, result.index))}
                  onToggleFalsePositive={() => toggleFalsePositive(record.jobId, result.index, result.reviewStatus)}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { buttonClass, buttonSecondaryClass, ErrorText } from "@/components/Card";
import { EvidenceFrames } from "@/components/media/EvidenceFrames";
import { Field, RegulatoryReference, ReviewBadge } from "@/components/media/EventDetails";
import { VideoPlayer, type VideoPlayerHandle } from "@/components/media/VideoPlayer";
import { plural } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { api, JobError, toViolationEvents, waitForJob } from "@/lib/api";
import { formatFileSize, formatTimecode } from "@/lib/format";
import type { ViolationEvent } from "@/lib/types";

type Phase = "idle" | "uploading" | "processing" | "completed" | "failed";

export function InferenceDemo() {
  const { locale, t } = useI18n();
  const ti = t.inference;
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<ViolationEvent[]>([]);

  const inputRef = useRef<HTMLInputElement>(null);
  const playerRef = useRef<VideoPlayerHandle>(null);
  const playerBoxRef = useRef<HTMLDivElement>(null);
  const runRef = useRef<AbortController | null>(null);
  const urlRef = useRef<string | null>(null);

  const busy = phase === "uploading" || phase === "processing";

  // Stop polling and release the local video URL when leaving the page.
  useEffect(
    () => () => {
      runRef.current?.abort();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  function selectFile(next: File | undefined) {
    if (!next || busy) return;
    const problem = !/\.mov$/i.test(next.name) ? ti.onlyMov : next.size === 0 ? ti.empty : null;
    setFileError(problem);
    if (problem) return;
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    // The uploaded file plays from memory; nothing leaves the machine except the upload itself.
    urlRef.current = URL.createObjectURL(next);
    setVideoUrl(urlRef.current);
    setFile(next);
    setPhase("idle");
    setError(null);
    setEvents([]);
  }

  async function analyze() {
    if (!file || busy) return;
    runRef.current?.abort();
    const run = new AbortController();
    runRef.current = run;
    setError(null);
    setEvents([]);
    setPhase("uploading");
    try {
      const { job_id } = await api.analyze(file, run.signal);
      setPhase("processing");
      const job = await waitForJob(job_id, run.signal);
      setEvents(toViolationEvents(job.violations, ti.unclassified));
      setPhase("completed");
    } catch (e) {
      if (run.signal.aborted) return;
      setError(e instanceof JobError ? ti.errors[e.code] : e instanceof Error ? e.message : String(e));
      setPhase("failed");
    }
  }

  function jumpTo(sec: number) {
    playerRef.current?.seekTo(sec);
    playerBoxRef.current?.scrollIntoView({ block: "nearest" });
  }

  return (
    <div className="flex flex-col gap-10">
      {/* 4.1 Upload */}
      <section className="flex flex-col gap-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!busy) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            selectFile(e.dataTransfer.files[0]);
          }}
          className={`flex flex-col items-center gap-3 rounded-2xl border border-dashed px-6 py-10 text-center transition-colors ${
            dragging ? "border-primary bg-surface-muted" : "border-border"
          }`}
        >
          <p className="text-base font-semibold">{ti.drop}</p>
          <p className="text-sm text-muted">{ti.dropHint}</p>
          <input
            ref={inputRef}
            type="file"
            accept=".mov,video/quicktime"
            className="sr-only"
            onChange={(e) => {
              selectFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className={`${buttonSecondaryClass} disabled:opacity-50`}
          >
            {file ? ti.replace : ti.choose}
          </button>
        </div>

        <ErrorText error={fileError} prefix={ti.errorPrefix} />

        {file && (
          <div className="flex flex-col gap-4 rounded-2xl border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{file.name}</p>
              <p className="text-xs tabular-nums text-muted">{formatFileSize(file.size, locale)}</p>
            </div>
            <button type="button" onClick={analyze} disabled={busy} className={buttonClass}>
              {ti.analyze}
            </button>
          </div>
        )}
      </section>

      {/* 4.2 Processing state. The backend reports no real progress, so the bar is indeterminate. */}
      {phase !== "idle" && (
        <section aria-live="polite" className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
            {ti.status} · <span className="text-foreground">{ti.phases[phase]}</span>
          </p>
          {busy && (
            <>
              <div className="h-1 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label={ti.progressLabel}>
                <div className="h-full w-2/5 rounded-full bg-primary motion-safe:animate-indeterminate" />
              </div>
              <p className="text-sm text-muted">
                {phase === "uploading" ? ti.uploadingMsg : ti.processingMsg}
              </p>
            </>
          )}
          {phase === "failed" && <ErrorText error={error} prefix={ti.errorPrefix} />}
        </section>
      )}

      {/* 4.3 Results */}
      {phase === "completed" && (
        <section className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <div ref={playerBoxRef} className="scroll-mt-24 lg:sticky lg:top-24 lg:self-start">
            <VideoPlayer
              ref={playerRef}
              src={videoUrl ?? undefined}
              label={file?.name ?? ti.uploadedRecording}
              markers={events.map((e) => ({ id: e.id, sec: e.timecodeSec, label: e.type }))}
            />
          </div>

          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2 rounded-2xl border border-border p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{ti.verdictLabel}</p>
              <h2 className="text-xl font-bold">
                {events.length > 0 ? ti.verdictFound : ti.verdictNone}
              </h2>
              <p className="text-sm text-muted">
                {events.length > 0
                  ? `${plural(locale, events.length, ti.flagged)} ${ti.flaggedNote}`
                  : ti.noneNote}
              </p>
            </div>

            {events.map((event) => (
              <article key={event.id} className="flex flex-col gap-4 rounded-2xl border border-border p-6">
                <ReviewBadge />
                <div className="flex items-baseline justify-between gap-4">
                  <h3 className="text-lg font-bold">{event.type}</h3>
                  <span className="shrink-0 text-sm font-semibold tabular-nums">{formatTimecode(event.timecodeSec)}</span>
                </div>
                <dl className="flex flex-col gap-4">
                  <Field label={t.fields.description}>{event.description || <span className="text-muted">{ti.noDescription}</span>}</Field>
                  <Field label={t.fields.evidence}>
                    <EvidenceFrames frames={event.evidenceFrames} />
                  </Field>
                  <Field label={t.fields.rule}>
                    <RegulatoryReference source={event.regulatorySource} />
                  </Field>
                </dl>
                <button type="button" onClick={() => jumpTo(event.timecodeSec)} className={`${buttonSecondaryClass} self-start`}>
                  {ti.jump}
                </button>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

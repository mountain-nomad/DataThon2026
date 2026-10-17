"use client";

import { useEffect, useRef, useState } from "react";
import { buttonClass, buttonSecondaryClass, ErrorText } from "@/components/Card";
import { EpisodeMedia } from "@/components/media/EpisodeMedia";
import { VideoPlayer } from "@/components/media/VideoPlayer";
import { useI18n } from "@/i18n/I18nProvider";
import { api, JobError, toPipelineResult, waitForJob } from "@/lib/api";
import { formatFileSize, formatTimecodePrecise } from "@/lib/format";
import type { PipelineResult, SpecialistResult } from "@/lib/types";
import { StageProgress, type StageState } from "./StageProgress";
import { StageResults } from "./StageResults";

type Phase = "idle" | "uploading" | "processing" | "completed" | "failed";

// Pause between revealing two stages, so each result appears on its own.
const REVEAL_MS = 900;

export function InferenceDemo() {
  const { locale, t } = useI18n();
  const ti = t.inference;
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  // Stages the backend reported as finished, and whether it reports them at all. Without that,
  // the stages are only a presentation of the finished result, never fake milestones.
  const [stagesDone, setStagesDone] = useState(0);
  const [tracked, setTracked] = useState(false);
  const [shown, setShown] = useState(0);
  const [selectedId, setSelectedId] = useState<string>();

  const inputRef = useRef<HTMLInputElement>(null);
  const videoBoxRef = useRef<HTMLElement>(null);
  const runRef = useRef<AbortController | null>(null);
  const urlRef = useRef<string | null>(null);

  const busy = phase === "uploading" || phase === "processing";
  const target = phase === "completed" ? 3 : stagesDone;

  // Stop polling and release the local video URL when leaving the page.
  useEffect(
    () => () => {
      runRef.current?.abort();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  // Reveal finished stages one at a time, left to right.
  useEffect(() => {
    if (shown >= target) return;
    const id = setTimeout(() => setShown((s) => s + 1), REVEAL_MS);
    return () => clearTimeout(id);
  }, [shown, target]);

  function reset() {
    runRef.current?.abort();
    setError(null);
    setResult(null);
    setStagesDone(0);
    setTracked(false);
    setShown(0);
    setSelectedId(undefined);
  }

  function selectFile(next: File | undefined) {
    if (!next || busy) return;
    const problem = !/\.mov$/i.test(next.name) ? ti.onlyMov : next.size === 0 ? ti.empty : null;
    setFileError(problem);
    if (problem) return;
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    // The uploaded file plays from memory right away; nothing leaves the machine except the upload.
    urlRef.current = URL.createObjectURL(next);
    setVideoUrl(urlRef.current);
    setFile(next);
    setPhase("idle");
    reset();
  }

  async function analyze() {
    if (!file || busy) return;
    reset();
    const run = new AbortController();
    runRef.current = run;
    setPhase("uploading");
    try {
      const { job_id } = await api.analyze(file, run.signal);
      setPhase("processing");
      const job = await waitForJob(job_id, run.signal, (update) => {
        if (run.signal.aborted || update.status !== "processing") return;
        if (typeof update.stages_done === "number") {
          setTracked(true);
          setStagesDone(Math.max(0, Math.min(3, update.stages_done)));
        }
        setResult(toPipelineResult(update));
      });
      setResult(toPipelineResult(job));
      setStagesDone(3);
      setPhase("completed");
    } catch (e) {
      if (run.signal.aborted) return;
      setError(e instanceof JobError ? ti.errors[e.code] : e instanceof Error ? e.message : String(e));
      setPhase("failed");
    }
  }

  const running = busy || shown < target;
  const stageState = (i: number): StageState =>
    i <= shown ? "done" : !running ? "pending" : tracked || phase === "completed" ? (i === shown + 1 ? "active" : "pending") : "active";
  const states: [StageState, StageState, StageState, StageState] = ["done", stageState(1), stageState(2), stageState(3)];

  const violations = (result?.results ?? []).filter((r) => r.status === "violation");
  const selected = violations.find((v) => v.id === selectedId) ?? violations[0];
  // Stage 3 is shown and something was found: the original moves left, the episode appears right.
  const split = shown >= 3 && selected !== undefined;

  function select(id: string) {
    setSelectedId(id);
    videoBoxRef.current?.scrollIntoView({ block: "nearest" });
  }

  return (
    <div className="flex flex-col gap-10">
      {/* Upload */}
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

      {videoUrl && file && (
        <>
          {/* Original video; turns into original + violation episode once stage 3 is shown. */}
          <section
            ref={videoBoxRef}
            className={`grid scroll-mt-24 grid-cols-1 motion-safe:transition-[grid-template-columns,column-gap] motion-safe:duration-700 motion-safe:ease-out ${
              split
                ? "gap-6 md:grid-cols-[1.2fr_1fr]"
                : "md:grid-cols-[1fr_0fr] md:gap-x-0"
            }`}
          >
            <div className="min-w-0">
              <VideoPlayer
                src={videoUrl}
                fallbackSrc={result?.previewUrl}
                label={file.name}
                ranges={
                  shown >= 3
                    ? violations
                        .filter((v) => v.startSec !== undefined)
                        .map((v) => ({
                          id: v.id,
                          start: v.startSec!,
                          end: v.endSec ?? v.startSec!,
                          label: v.ruleId ?? ti.status.violation,
                          active: v.id === selected?.id,
                        }))
                    : []
                }
                onRangeClick={setSelectedId}
              />
            </div>
            <div className="min-w-0 overflow-hidden">
              {split && (
                <Episode
                  key={selected.id}
                  violation={selected}
                  violations={violations}
                  src={videoUrl}
                  fallbackSrc={result?.previewUrl}
                  onSelect={setSelectedId}
                />
              )}
            </div>
          </section>

          {/* AI stages */}
          <section className="flex flex-col gap-6">
            <StageProgress states={states} />
            <div aria-live="polite" className="flex flex-col gap-2 text-center text-sm text-muted">
              {phase === "uploading" && <p>{ti.uploadingMsg}</p>}
              {phase === "processing" && <p>{ti.processingMsg}</p>}
              {phase === "completed" && !tracked && <p>{ti.replayNote}</p>}
              {phase === "failed" && <ErrorText error={error} prefix={ti.errorPrefix} />}
            </div>
            <StageResults shown={shown} result={result} selectedId={selected?.id} onSelect={select} />
          </section>
        </>
      )}
    </div>
  );
}

// Right column: the localized episode of the selected violation.
function Episode({
  violation,
  violations,
  src,
  fallbackSrc,
  onSelect,
}: {
  violation: SpecialistResult;
  violations: SpecialistResult[];
  src: string;
  fallbackSrc?: string;
  onSelect: (id: string) => void;
}) {
  const { t } = useI18n();
  const ti = t.inference;
  const { startSec, endSec } = violation;

  return (
    <div className="flex flex-col gap-3 motion-safe:animate-reveal">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
          {ti.episode}
          {startSec !== undefined && (
            <span className="tabular-nums text-foreground">
              {" · "}
              {formatTimecodePrecise(startSec)}
              {endSec !== undefined && endSec > startSec && ` – ${formatTimecodePrecise(endSec)}`}
            </span>
          )}
        </p>
        {violations.length > 1 && (
          <div role="group" aria-label={ti.selectViolation} className="flex gap-1">
            {violations.map((v, i) => (
              <button
                key={v.id}
                type="button"
                aria-pressed={v.id === violation.id}
                onClick={() => onSelect(v.id)}
                className={`size-7 rounded-full border text-xs font-semibold tabular-nums transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                  v.id === violation.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-surface text-foreground hover:bg-surface-muted"
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>
      <EpisodeMedia
        result={violation}
        src={src}
        fallbackSrc={fallbackSrc}
        label={startSec === undefined ? ti.episode : `${ti.episode} · ${formatTimecodePrecise(startSec)}`}
      />
    </div>
  );
}

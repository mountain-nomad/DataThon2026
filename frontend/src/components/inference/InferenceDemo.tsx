"use client";

import { useEffect, useRef, useState } from "react";
import { buttonClass, buttonSecondaryClass, ErrorText } from "@/components/Card";
import { EvidenceFrames } from "@/components/media/EvidenceFrames";
import { Field, RegulatoryReference, ReviewBadge } from "@/components/media/EventDetails";
import { VideoPlayer, type VideoPlayerHandle } from "@/components/media/VideoPlayer";
import { api, toViolationEvents, waitForJob } from "@/lib/api";
import { formatFileSize, formatTimecode } from "@/lib/format";
import type { ViolationEvent } from "@/lib/types";

type Phase = "idle" | "uploading" | "processing" | "completed" | "failed";

const PHASE_LABEL: Record<Exclude<Phase, "idle">, string> = {
  uploading: "Uploading",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

function validate(file: File): string | null {
  if (!/\.mov$/i.test(file.name)) return "Only .mov files are accepted.";
  if (file.size === 0) return "The file is empty.";
  return null;
}

export function InferenceDemo() {
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
    const problem = validate(next);
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
      setEvents(toViolationEvents(job.violations));
      setPhase("completed");
    } catch (e) {
      if (run.signal.aborted) return;
      setError(e instanceof Error ? e.message : String(e));
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
          <p className="text-base font-semibold">Drop a .mov recording here</p>
          <p className="text-sm text-muted">or choose it from your computer. The file is analysed locally.</p>
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
            {file ? "Replace file" : "Choose file"}
          </button>
        </div>

        <ErrorText error={fileError} />

        {file && (
          <div className="flex flex-col gap-4 rounded-2xl border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{file.name}</p>
              <p className="text-xs tabular-nums text-muted">{formatFileSize(file.size)}</p>
            </div>
            <button type="button" onClick={analyze} disabled={busy} className={buttonClass}>
              Analyze Video
            </button>
          </div>
        )}
      </section>

      {/* 4.2 Processing state. The backend reports no real progress, so the bar is indeterminate. */}
      {phase !== "idle" && (
        <section aria-live="polite" className="flex flex-col gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
            Status · <span className="text-foreground">{PHASE_LABEL[phase]}</span>
          </p>
          {busy && (
            <>
              <div className="h-1 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label="Analysis in progress">
                <div className="h-full w-2/5 rounded-full bg-primary motion-safe:animate-indeterminate" />
              </div>
              <p className="text-sm text-muted">
                {phase === "uploading" ? "Uploading the recording…" : "AI analysis is running. This can take a few minutes."}
              </p>
            </>
          )}
          {phase === "failed" && <ErrorText error={error} />}
        </section>
      )}

      {/* 4.3 Results */}
      {phase === "completed" && (
        <section className="grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <div ref={playerBoxRef} className="scroll-mt-24 lg:sticky lg:top-24 lg:self-start">
            <VideoPlayer
              ref={playerRef}
              src={videoUrl ?? undefined}
              label={file?.name ?? "Uploaded recording"}
              markers={events.map((e) => ({ id: e.id, sec: e.timecodeSec, label: e.type }))}
            />
          </div>

          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2 rounded-2xl border border-border p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">Overall verdict</p>
              <h2 className="text-xl font-bold">
                {events.length > 0 ? "Potential violations detected" : "No violations detected"}
              </h2>
              <p className="text-sm text-muted">
                {events.length > 0
                  ? `The model flagged ${events.length} ${events.length === 1 ? "event" : "events"}. These are AI detections, not established violations: each one needs review by a person.`
                  : "The model flagged nothing in this recording. This is an AI result, not a guarantee."}
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
                  <Field label="Description">{event.description || <span className="text-muted">No description returned.</span>}</Field>
                  <Field label="Evidence frames">
                    <EvidenceFrames frames={event.evidenceFrames} />
                  </Field>
                  <Field label="Referenced rule">
                    <RegulatoryReference source={event.regulatorySource} />
                  </Field>
                </dl>
                <button type="button" onClick={() => jumpTo(event.timecodeSec)} className={`${buttonSecondaryClass} self-start`}>
                  Jump to timestamp
                </button>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

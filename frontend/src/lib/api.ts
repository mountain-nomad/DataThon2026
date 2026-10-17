// Client for the analysis API (backend_description.md). The browser only calls same-origin
// /api/*: the upload goes to the jury endpoint /api/v1/analyze (the Next server adds X-API-Key),
// progress and the pipeline result come from the UI endpoint /api/jobs/{id}/pipeline.

import {
  SCENARIOS,
  type AnalysisRecord,
  type EvidenceFrame,
  type LegalBasis,
  type PipelineResult,
  type ReviewStatus,
  type ScenarioResult,
  type SpecialistResult,
} from "./types";

export type JobStatus = "processing" | "done" | "failed";

// snake_case shapes. Frames are read leniently because the final contract is not published yet.
type RawFrame = string | { timestamp_sec?: number; image_base64?: string; image?: string };

interface RawSpecialist {
  scenario?: string | null;
  rule_id?: string | null;
  status: string;
  quote?: string | null;
  evidence?: string | null;
  start_sec?: number | null;
  end_sec?: number | null;
  evidence_frames?: RawFrame[];
  legal_basis?: RawLegalBasis | null;
  review_status?: ReviewStatus | null;
}

interface RawLegalBasis {
  type_id?: string | null;
  name?: string | null;
  mapping_status?: string | null;
  limitations?: string | null;
  rules?: {
    rule_id: string;
    clause: string;
    summary?: string | null;
    human_verified?: boolean;
    qualifier?: string | null;
    source?: { source_id?: string; title?: string; url?: string; binding?: boolean };
  }[];
}

export interface RawPipelineJob {
  job_id: string;
  status: JobStatus;
  error?: string | null;
  // 0–3 while processing; null when the backend doesn't track stages.
  stages_done?: number | null;
  preview_url?: string | null;
  file_name?: string | null;
  created_at?: string | null;
  duration_sec?: number | null;
  scenario?: { primary: string; secondary?: string | null } | null;
  specialist_results?: RawSpecialist[] | null;
}

// Client-side failures, translated by the UI. Server messages (`detail`, `error`) are shown as-is.
export class JobError extends Error {
  constructor(readonly code: "timeout" | "network" | "jobFailed") {
    super(code);
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ? String(body.detail) : `${res.status} ${res.statusText}`, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  analyze: (file: File, signal?: AbortSignal) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ job_id: string }>("/v1/analyze", { method: "POST", body: form, signal });
  },
  pipeline: (jobId: string, signal?: AbortSignal) =>
    request<RawPipelineJob>(`/jobs/${encodeURIComponent(jobId)}/pipeline`, { signal }),
  // Finished analyses, newest first: the history behind /demo-dashboard.
  jobs: (signal?: AbortSignal) => request<{ items: RawPipelineJob[] }>("/jobs?status=done", { signal }),
  review: (jobId: string, index: number, review_status: ReviewStatus) =>
    request<RawSpecialist>(`/jobs/${encodeURIComponent(jobId)}/results/${index}/review`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ review_status }),
    }),
};

export const POLL_INTERVAL_MS = 2500;
export const JOB_TIMEOUT_MS = 5 * 60 * 1000;
const MAX_NETWORK_ERRORS = 3;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Polls until the job is done; `onPoll` sees every intermediate state (for stage progress).
// Throws on `failed`, on timeout, or after repeated network errors.
export async function waitForJob(
  jobId: string,
  signal: AbortSignal,
  onPoll?: (job: RawPipelineJob) => void,
): Promise<RawPipelineJob> {
  const startedAt = Date.now();
  let networkErrors = 0;
  for (;;) {
    await sleep(POLL_INTERVAL_MS);
    signal.throwIfAborted();
    if (Date.now() - startedAt > JOB_TIMEOUT_MS) {
      throw new JobError("timeout");
    }
    let job: RawPipelineJob;
    try {
      job = await api.pipeline(jobId, signal);
      networkErrors = 0;
    } catch (e) {
      if (signal.aborted || e instanceof ApiError) throw e;
      if (++networkErrors >= MAX_NETWORK_ERRORS) {
        throw new JobError("network");
      }
      continue;
    }
    onPoll?.(job);
    if (job.status === "done") return job;
    if (job.status === "failed") {
      throw job.error ? new Error(job.error) : new JobError("jobFailed");
    }
  }
}

function toFrame(raw: RawFrame, fallbackSec: number): EvidenceFrame {
  if (typeof raw === "string") return { timestampSec: fallbackSec, imageBase64: raw };
  return { timestampSec: raw.timestamp_sec ?? fallbackSec, imageBase64: raw.image_base64 ?? raw.image ?? "" };
}

// "COUNTING / DEPOSIT WITHOUT CLIENT" or "counting_deposit_without_client" -> the canonical id.
// Labels outside the 7 router classes are returned unchanged and shown as-is.
export function normalizeScenario(raw: string): string {
  const id = raw
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  return (SCENARIOS as readonly string[]).includes(id) ? id : raw;
}

function toLegalBasis(raw: RawLegalBasis | null | undefined): LegalBasis | undefined {
  if (!raw) return undefined;
  return {
    typeId: raw.type_id ?? undefined,
    name: raw.name ?? undefined,
    mappingStatus: raw.mapping_status ?? undefined,
    limitations: raw.limitations ?? undefined,
    clauses: (raw.rules ?? []).map((c) => ({
      ruleId: c.rule_id,
      clause: c.clause,
      summary: c.summary ?? undefined,
      humanVerified: c.human_verified === true,
      qualifier: c.qualifier ?? undefined,
      source: {
        sourceId: c.source?.source_id ?? "",
        title: c.source?.title ?? c.source?.source_id ?? "",
        url: c.source?.url || undefined,
        binding: c.source?.binding !== false,
      },
    })),
  };
}

const num = (v: number | null | undefined) => (typeof v === "number" && Number.isFinite(v) ? v : undefined);

function toScenario(raw: RawPipelineJob["scenario"]): ScenarioResult | null {
  if (!raw?.primary) return null;
  const primary = normalizeScenario(raw.primary);
  const secondary = raw.secondary ? normalizeScenario(raw.secondary) : undefined;
  return { primary, secondary: secondary !== primary ? secondary : undefined };
}

// Only results that belong to a routed scenario are kept: a specialist's verdict is meaningful
// only for the scenario it checks. Results without a scenario belong to the primary one.
export function toPipelineResult(job: RawPipelineJob): PipelineResult {
  const scenario = toScenario(job.scenario);
  const routed = new Set([scenario?.primary, scenario?.secondary].filter(Boolean));
  const results: SpecialistResult[] = (job.specialist_results ?? [])
    .map((r, i) => {
      const startSec = num(r.start_sec);
      return {
        id: String(i + 1),
        index: i,
        scenario: r.scenario ? normalizeScenario(r.scenario) : scenario?.primary,
        ruleId: r.rule_id ?? undefined,
        status: r.status,
        quote: r.quote ?? "",
        evidence: r.evidence ?? "",
        startSec,
        endSec: num(r.end_sec),
        evidenceFrames: (r.evidence_frames ?? []).slice(0, 3).map((f) => toFrame(f, startSec ?? 0)),
        legalBasis: toLegalBasis(r.legal_basis),
        reviewStatus:
          r.status !== "violation" ? undefined : r.review_status === "false_positive" ? "false_positive" : "pending",
      } satisfies SpecialistResult;
    })
    .filter((r) => !scenario || (r.scenario !== undefined && routed.has(r.scenario)))
    // Chronological; results without a time go last.
    .sort((a, b) => (a.startSec ?? Infinity) - (b.startSec ?? Infinity));
  return { scenario, results, previewUrl: job.preview_url ?? undefined };
}

export function toAnalysisRecord(job: RawPipelineJob): AnalysisRecord {
  return {
    ...toPipelineResult(job),
    jobId: job.job_id,
    fileName: job.file_name ?? "",
    createdAt: job.created_at ?? "",
    durationSec: num(job.duration_sec),
  };
}

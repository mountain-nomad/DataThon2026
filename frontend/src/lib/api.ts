// Client for the analysis API (frontend_description.md §7). The browser only calls same-origin
// /api/*, which next.config.ts rewrites to the backend. The backend adds X-API-Key, so the key
// never ships in the JS bundle.

import type { EvidenceFrame, ViolationEvent } from "./types";

export type JobStatus = "processing" | "done" | "failed";

// Jury API shapes (snake_case). Only what the UI reads is typed; frame and type field names are
// read leniently because the final contract is not published yet.
type RawFrame = string | { timestamp_sec?: number; image_base64?: string; image?: string };

interface RawViolation {
  id?: string | number;
  type?: string;
  violation_type?: string;
  timecode_sec: number;
  description?: string;
  evidence_frames?: RawFrame[];
}

export interface RawJob {
  job_id: string;
  status: JobStatus;
  verdict?: unknown;
  violations?: RawViolation[];
  error?: string;
  detail?: string;
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
  job: (jobId: string, signal?: AbortSignal) =>
    request<RawJob>(`/v1/jobs/${encodeURIComponent(jobId)}`, { signal }),
};

export const POLL_INTERVAL_MS = 2500;
export const JOB_TIMEOUT_MS = 5 * 60 * 1000;
const MAX_NETWORK_ERRORS = 3;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Polls until the job is done. Throws on `failed`, on timeout, or after repeated network errors.
export async function waitForJob(jobId: string, signal: AbortSignal): Promise<RawJob> {
  const startedAt = Date.now();
  let networkErrors = 0;
  for (;;) {
    await sleep(POLL_INTERVAL_MS);
    signal.throwIfAborted();
    if (Date.now() - startedAt > JOB_TIMEOUT_MS) {
      throw new Error("No result after 5 minutes. The analysis may still be running on the server.");
    }
    let job: RawJob;
    try {
      job = await api.job(jobId, signal);
      networkErrors = 0;
    } catch (e) {
      if (signal.aborted || e instanceof ApiError) throw e;
      if (++networkErrors >= MAX_NETWORK_ERRORS) {
        throw new Error("Lost connection to the backend while waiting for the result.");
      }
      continue;
    }
    if (job.status === "done") return job;
    if (job.status === "failed") throw new Error(job.error ?? job.detail ?? "The analysis failed on the server.");
  }
}

function toFrame(raw: RawFrame, fallbackSec: number): EvidenceFrame {
  if (typeof raw === "string") return { timestampSec: fallbackSec, imageBase64: raw };
  return { timestampSec: raw.timestamp_sec ?? fallbackSec, imageBase64: raw.image_base64 ?? raw.image ?? "" };
}

// Adapts the jury response to the frontend model. Fields the jury API doesn't carry
// (processName, clipUrl, regulatorySource) stay empty; reviewStatus starts as pending.
export function toViolationEvents(raw: RawViolation[] | undefined): ViolationEvent[] {
  return (raw ?? []).map((v, i) => ({
    id: String(v.id ?? i + 1),
    type: v.type ?? v.violation_type ?? "Unclassified",
    description: v.description ?? "",
    timecodeSec: v.timecode_sec,
    evidenceFrames: (v.evidence_frames ?? []).slice(0, 3).map((f) => toFrame(f, v.timecode_sec)),
    reviewStatus: "pending",
  }));
}

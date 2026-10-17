// Typed client for the backend. All calls go through the /api rewrite in next.config.ts.

export type FeatureRecord = Record<string, unknown>;

export interface Prediction {
  prediction: unknown;
  probabilities?: Record<string, number> | null;
}

export interface PredictResponse {
  model_version: string;
  predictions: Prediction[];
}

export interface ModelInfo {
  loaded: boolean;
  version: string;
  task?: string | null;
  target?: string | null;
  features: string[];
  metrics: Record<string, number>;
  example?: FeatureRecord | null;
}

export interface Health {
  status: string;
  ml: { status: string; model_loaded?: boolean; model_version?: string; detail?: string };
}

export interface PredictionLog {
  id: number;
  created_at: string;
  model_version: string;
  input: FeatureRecord;
  output: Prediction;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? String(body.detail) : `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  model: () => request<ModelInfo>("/model"),
  predict: (records: FeatureRecord[]) =>
    request<PredictResponse>("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ records }),
    }),
  predictCsv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<PredictResponse>("/predict/csv", { method: "POST", body: form });
  },
  predictions: (limit = 20) => request<PredictionLog[]>(`/predictions?limit=${limit}`),
};

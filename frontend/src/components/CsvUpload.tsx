"use client";

import { useState } from "react";
import { api, type PredictResponse } from "@/lib/api";
import { buttonClass, Card, ErrorText, inputClass } from "./Card";
import { PredictionResult } from "./PredictionResult";

export function CsvUpload({ onPredicted }: { onPredicted?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit() {
    if (!file) return;
    setError(null);
    setLoading(true);
    try {
      setResult(await api.predictCsv(file));
      onPredicted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Batch prediction (CSV)">
      <p className="text-sm text-muted">CSV with a header row of feature names.</p>
      <input
        type="file"
        accept=".csv,text/csv"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className={`${inputClass} file:mr-3 file:rounded-full file:border-0 file:bg-surface file:px-4 file:py-1.5 file:font-semibold file:text-primary`}
      />
      <button onClick={submit} disabled={!file || loading} className={buttonClass}>
        {loading ? "Uploading…" : "Run batch"}
      </button>
      <ErrorText error={error} />
      <PredictionResult result={result} />
    </Card>
  );
}

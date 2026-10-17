"use client";

import { useEffect, useState } from "react";
import { api, type PredictResponse } from "@/lib/api";
import { buttonClass, Card, ErrorText, inputClass } from "./Card";
import { PredictionResult } from "./PredictionResult";

export function PredictForm({ onPredicted }: { onPredicted?: () => void }) {
  const [input, setInput] = useState("{}");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Prefill with an example row saved alongside the model at training time.
  useEffect(() => {
    api
      .model()
      .then((m) => m.example && setInput(JSON.stringify(m.example, null, 2)))
      .catch(() => {});
  }, []);

  async function submit() {
    setError(null);
    setLoading(true);
    try {
      const parsed = JSON.parse(input);
      setResult(await api.predict(Array.isArray(parsed) ? parsed : [parsed]));
      onPredicted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="Single prediction">
      <p className="text-sm text-muted">JSON object (one row) or array of rows.</p>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        rows={8}
        spellCheck={false}
        className={`font-mono ${inputClass}`}
      />
      <button onClick={submit} disabled={loading} className={buttonClass}>
        {loading ? "Predicting…" : "Predict"}
      </button>
      <ErrorText error={error} />
      <PredictionResult result={result} />
    </Card>
  );
}

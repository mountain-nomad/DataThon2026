"use client";

import { useState } from "react";
import { buttonClass, ErrorText } from "@/components/Card";
import { api, type PredictResponse } from "@/lib/api";
import { useModel } from "./useModel";

// One accent: the winning class is magenta, the rest stay neutral.
const barColor = (rank: number) => (rank === 0 ? "bg-primary" : "bg-muted/40");

export function TryExample() {
  const state = useModel();
  const example = state.status === "ready" ? state.model.example : null;
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!example) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.predict([example]));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const pred = result?.predictions[0];
  const probs = pred?.probabilities ? Object.entries(pred.probabilities).sort(([, a], [, b]) => b - a) : [];

  return (
    <div className="grid gap-6 rounded-2xl border border-border bg-surface p-6 md:grid-cols-2 md:p-8">
      <div className="flex flex-col gap-4">
        <p className="text-[13px] text-muted">Request: one record from the training data</p>
        <pre className="min-h-40 overflow-x-auto rounded-xl bg-surface-muted p-4 font-mono text-[13px] leading-relaxed">
          {example ? JSON.stringify(example, null, 2) : "No example available yet."}
        </pre>
        <button onClick={run} disabled={!example || loading} className={buttonClass}>
          {loading ? "Predicting…" : "Run this record"}
        </button>
      </div>

      <div className="flex flex-col gap-4" aria-live="polite">
        <p className="text-[13px] text-muted">Response</p>
        <ErrorText error={error} />
        {pred ? (
          <>
            <p className="text-[32px] font-bold leading-tight">{String(pred.prediction)}</p>
            {probs.length > 0 && (
              <ul className="flex flex-col gap-3">
                {probs.map(([label, p], i) => (
                  <li key={label} className="grid grid-cols-[minmax(0,7rem)_1fr_3.5rem] items-center gap-3 text-sm">
                    <span className="truncate">{label}</span>
                    <span className="h-2 rounded-full bg-surface-muted">
                      <span
                        className={`block h-full rounded-full ${barColor(i)}`}
                        style={{ width: `${(p * 100).toFixed(1)}%` }}
                      />
                    </span>
                    <span className="text-right tabular-nums">{(p * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-[13px] text-muted">
              Model {result.model_version}. This call is now in the dashboard history.
            </p>
          </>
        ) : (
          <p className="text-sm text-muted">The model&apos;s answer and its confidence per class will appear here.</p>
        )}
      </div>
    </div>
  );
}

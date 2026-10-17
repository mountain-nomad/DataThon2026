import type { PredictResponse } from "@/lib/api";

export function PredictionResult({ result }: { result: PredictResponse | null }) {
  if (!result) return null;
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-muted">
        {result.predictions.length} prediction(s) · model {result.model_version}
      </p>
      <ul className="flex max-h-80 flex-col gap-2 overflow-auto">
        {result.predictions.map((p, i) => (
          <li key={i} className="rounded-xl bg-surface-muted px-4 py-3">
            <span className="text-base font-bold">{String(p.prediction)}</span>
            {p.probabilities && (
              <div className="mt-2 flex flex-col gap-1.5">
                {Object.entries(p.probabilities)
                  .sort(([, a], [, b]) => b - a)
                  .map(([label, v]) => (
                    <div key={label} className="grid grid-cols-[6rem_1fr_3.5rem] items-center gap-3">
                      <span className="truncate text-muted">{label}</span>
                      <span className="h-1.5 rounded-full bg-border">
                        <span
                          className="block h-full rounded-full bg-primary"
                          style={{ width: `${(v * 100).toFixed(1)}%` }}
                        />
                      </span>
                      <span className="text-right tabular-nums">{(v * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

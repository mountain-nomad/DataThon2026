"use client";

import { useEffect, useState } from "react";
import { api, type PredictionLog } from "@/lib/api";
import { Card, ErrorText } from "./Card";

export function HistoryTable({ refreshKey }: { refreshKey: number }) {
  const [rows, setRows] = useState<PredictionLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .predictions(20)
      .then((r) => {
        setRows(r);
        setError(null);
      })
      .catch((e) => setError(e.message));
  }, [refreshKey]);

  return (
    <Card title="Recent predictions">
      <ErrorText error={error} />
      {rows.length === 0 ? (
        <p className="text-sm text-muted">No predictions yet.</p>
      ) : (
        <div className="-mx-2 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-[13px] text-muted">
              <tr>
                <th className="px-2 py-2 font-semibold">#</th>
                <th className="px-2 py-2 font-semibold">Time</th>
                <th className="px-2 py-2 font-semibold">Prediction</th>
                <th className="px-2 py-2 font-semibold">Input</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-border hover:bg-surface-muted/60">
                  <td className="px-2 py-2 text-muted">{r.id}</td>
                  <td className="px-2 py-2 whitespace-nowrap">
                    {new Date(r.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-2 py-2 font-semibold">{String(r.output.prediction)}</td>
                  <td className="max-w-md truncate px-2 py-2 font-mono text-xs text-muted">
                    {JSON.stringify(r.input)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

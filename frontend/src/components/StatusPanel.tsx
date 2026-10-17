"use client";

import { useEffect, useState } from "react";
import { api, type Health, type ModelInfo } from "@/lib/api";
import { Card, ErrorText, StatusDot } from "./Card";

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="flex items-center gap-2 font-semibold tabular-nums">{children}</dd>
    </div>
  );
}

export function StatusPanel() {
  const [health, setHealth] = useState<Health | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(`Backend: ${e.message}`));
    api.model().then(setModel).catch(() => {});
  }, []);

  const backendOk = health ? true : error ? false : null;
  const mlOk = health ? health.ml.status === "ok" : backendOk === false ? false : null;

  return (
    <Card title="System status">
      <ErrorText error={error} />
      <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Stat label="Backend">
          <StatusDot ok={backendOk} />
          {backendOk === null ? "…" : backendOk ? "Up" : "Down"}
        </Stat>
        <Stat label="ML service">
          <StatusDot ok={mlOk} />
          {mlOk === null ? "…" : mlOk ? "Up" : (health?.ml.detail ?? "Down")}
        </Stat>
        <Stat label="Model">
          {model ? (model.loaded ? `${model.version}` : "Dummy (not trained)") : "…"}
        </Stat>
        <Stat label="Task">{model?.task ?? "—"}</Stat>
        {model &&
          Object.entries(model.metrics).map(([k, v]) => (
            <Stat key={k} label={k}>
              <span className="text-2xl font-bold text-primary">{v.toFixed(4)}</span>
            </Stat>
          ))}
      </dl>
    </Card>
  );
}

"use client";

import { useModel } from "./useModel";

export function ModelFacts() {
  const state = useModel();
  if (state.status !== "ready" || !state.model.loaded) {
    return (
      <p className="text-sm text-muted">
        {state.status === "loading" ? "Reading the current model…" : "Model details appear here once a model is trained and the services are running."}
      </p>
    );
  }
  const { model } = state;

  return (
    <div className="flex flex-col gap-8">
      <dl className="grid grid-cols-2 gap-x-8 gap-y-6">
        {Object.entries(model.metrics).map(([name, value]) => (
          <div key={name} className="border-t border-border pt-3">
            <dt className="text-[13px] text-muted">{name}</dt>
            <dd className="text-[32px] font-bold tabular-nums">{value.toFixed(4)}</dd>
          </div>
        ))}
        <div className="border-t border-border pt-3">
          <dt className="text-[13px] text-muted">Target</dt>
          <dd className="text-xl font-bold">{model.target ?? "—"}</dd>
        </div>
        <div className="border-t border-border pt-3">
          <dt className="text-[13px] text-muted">Task</dt>
          <dd className="text-xl font-bold capitalize">{model.task ?? "—"}</dd>
        </div>
      </dl>
      <div>
        <p className="mb-3 text-[13px] text-muted">Input features</p>
        <ul className="flex flex-wrap gap-2">
          {model.features.map((f) => (
            <li key={f} className="rounded-full bg-surface-muted px-3 py-1 text-sm">
              {f}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

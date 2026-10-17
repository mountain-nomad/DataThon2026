"use client";

import { StatusDot } from "@/components/Card";
import { useModel } from "./useModel";

// Sits on the coral end of the hero. It brings its own surface, so text never relies on the gradient there.
export function LiveModelCard() {
  const state = useModel();
  const ready = state.status === "ready" ? state : null;
  const metric = ready ? Object.entries(ready.model.metrics)[0] : undefined;

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <StatusDot ok={state.status === "loading" ? null : Boolean(ready?.mlUp)} />
        {state.status === "loading" ? "Connecting…" : ready?.mlUp ? "Model is live" : "Model offline"}
      </div>

      {ready?.model.loaded ? (
        <>
          <p className="mt-6 text-[13px] text-muted">{metric ? `Validation ${metric[0]}` : "Validation"}</p>
          <p className="text-5xl font-extrabold tabular-nums">
            {metric ? metric[1].toFixed(3) : "—"}
          </p>
          <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-4 text-sm">
            <div>
              <dt className="text-[13px] text-muted">Task</dt>
              <dd className="font-semibold capitalize">{ready.model.task}</dd>
            </div>
            <div>
              <dt className="text-[13px] text-muted">Features</dt>
              <dd className="font-semibold tabular-nums">{ready.model.features.length}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-[13px] text-muted">Version</dt>
              <dd className="font-semibold tabular-nums">{ready.model.version}</dd>
            </div>
          </dl>
        </>
      ) : (
        <p className="mt-4 text-sm text-muted">
          {state.status === "offline"
            ? "The backend isn't reachable. Start the services with make dev."
            : state.status === "ready"
              ? "No trained model yet. Run make train to create one."
              : "Reading the current model…"}
        </p>
      )}
    </div>
  );
}

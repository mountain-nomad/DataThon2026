"use client";

import { useI18n } from "@/i18n/I18nProvider";

export type StageState = "done" | "active" | "pending";

const CIRCLE: Record<StageState, string> = {
  // Strict pairs: magenta background = white text, white background = black text.
  done: "border-primary bg-primary text-primary-foreground",
  active: "border-primary bg-surface text-foreground",
  pending: "border-border bg-surface text-foreground",
};

// Connector from step i to step i+1: thin while waiting, thicker with a flowing wave while the
// next stage runs, then filled with the white -> magenta gradient once it is done.
function Connector({ state }: { state: StageState }) {
  return (
    <div aria-hidden className="absolute top-[18px] left-[calc(50%+26px)] flex h-1.5 w-[calc(100%-52px)] -translate-y-1/2 items-center">
      <div className={`w-full ${state === "active" ? "motion-safe:animate-wave" : ""}`}>
        <div
          className={`w-full rounded-full transition-[height,background-color] duration-500 ${
            state === "pending" ? "h-px bg-border" : state === "active" ? "h-1 bg-stage-flow motion-safe:animate-flow" : "h-1 bg-surface"
          }`}
        />
      </div>
      <div
        className={`absolute left-0 h-1 rounded-full bg-stage-done transition-[width] duration-700 ease-out ${
          state === "done" ? "w-full" : "w-0"
        }`}
      />
    </div>
  );
}

// Uploaded video -> the three AI stages. `states[0]` is the input, `states[1..3]` the stages.
export function StageProgress({ states }: { states: [StageState, StageState, StageState, StageState] }) {
  const { t } = useI18n();
  const ti = t.inference;
  const labels = [ti.stages.upload, ti.stages.scenario, ti.stages.violation, ti.stages.localization];
  return (
    <ol aria-label={ti.stagesLabel} className="grid grid-cols-4">
      {labels.map((label, i) => (
        <li key={label} className="relative flex flex-col items-center gap-2 text-center">
          {i < 3 && <Connector state={states[i + 1]} />}
          <span
            aria-hidden
            className={`relative flex size-9 items-center justify-center rounded-full border-2 text-xs font-bold tabular-nums transition-colors duration-500 ${CIRCLE[states[i]]}`}
          >
            {i === 0 ? (
              <svg viewBox="0 0 16 16" className="size-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m3.5 8.5 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              String(i).padStart(2, "0")
            )}
          </span>
          <span className={`px-1 text-xs leading-snug ${states[i] === "pending" ? "text-muted" : "font-semibold"}`}>
            {label}
            <span className="sr-only"> · {ti.stageState[states[i]]}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

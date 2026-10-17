"use client";

import { useState } from "react";
import { DEMO_CAMERAS, DEMO_EVENTS } from "@/lib/demo-data";
import type { ViolationEvent } from "@/lib/types";
import { CameraDialog } from "./CameraDialog";
import { CameraTile } from "./CameraTile";
import { EpisodeCard } from "./EpisodeCard";
import { ViolationStats } from "./ViolationStats";

function SectionTitle({ n, title, children }: { n: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="flex items-baseline gap-3 text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <span className="text-primary tabular-nums">{n}</span>
        {title}
      </p>
      {children && <p className="text-sm text-muted">{children}</p>}
    </div>
  );
}

export function MonitoringDashboard() {
  const cameras = DEMO_CAMERAS;
  const [events, setEvents] = useState<ViolationEvent[]>(DEMO_EVENTS);
  const [openCameraId, setOpenCameraId] = useState<string | null>(null);

  const cameraById = new Map(cameras.map((c) => [c.id, c]));
  const eventsFor = (cameraId: string) => events.filter((e) => e.cameraId === cameraId);
  const openCamera = openCameraId ? (cameraById.get(openCameraId) ?? null) : null;

  // Human review lives in its own field; the model's output is never edited.
  const toggleFalsePositive = (id: string) =>
    setEvents((list) =>
      list.map((e) =>
        e.id === id ? { ...e, reviewStatus: e.reviewStatus === "false_positive" ? "pending" : "false_positive" } : e,
      ),
    );

  return (
    <div className="flex flex-col gap-16">
      <section className="flex flex-col gap-6">
        <SectionTitle n="01" title="Cameras">
          Prerecorded demo footage played in a loop. This is not a live stream.
        </SectionTitle>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {cameras.map((camera) => (
            <CameraTile
              key={camera.id}
              camera={camera}
              events={eventsFor(camera.id)}
              onOpen={() => setOpenCameraId(camera.id)}
            />
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-6">
        <SectionTitle n="02" title="Detection statistics" />
        <ViolationStats events={events} />
      </section>

      <section className="flex flex-col gap-6">
        <SectionTitle n="03" title="Detected episodes">
          Every episode is an AI detection until a person reviews it.
        </SectionTitle>
        {events.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-border px-6 py-10 text-center text-sm text-muted">
            No episodes detected in the demo recordings.
          </p>
        ) : (
          <div className="flex flex-col gap-4">
            {events.map((event) => (
              <EpisodeCard
                key={event.id}
                event={event}
                camera={event.cameraId ? cameraById.get(event.cameraId) : undefined}
                onToggleFalsePositive={() => toggleFalsePositive(event.id)}
              />
            ))}
          </div>
        )}
      </section>

      <CameraDialog
        camera={openCamera}
        events={openCamera ? eventsFor(openCamera.id) : []}
        onClose={() => setOpenCameraId(null)}
      />
    </div>
  );
}

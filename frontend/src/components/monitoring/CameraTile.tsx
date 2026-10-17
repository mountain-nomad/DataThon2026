"use client";

import { useEffect, useRef, useState } from "react";
import { MediaPlaceholder } from "@/components/media/MediaPlaceholder";
import type { Camera, ViolationEvent } from "@/lib/types";

const STATUS: Record<"demo" | "playing" | "unavailable", { label: string; dot: string }> = {
  demo: { label: "Demo", dot: "bg-border" },
  playing: { label: "Playing", dot: "bg-forte-sky" },
  unavailable: { label: "Unavailable", dot: "bg-forte-coral" },
};

export function CameraTile({
  camera,
  events,
  onOpen,
}: {
  camera: Camera;
  events: ViolationEvent[];
  onOpen: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);

  // Decode only the tiles that are on screen: 16 parallel decoders would stall the page.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) video.play().catch(() => {});
        else video.pause();
      },
      { threshold: 0.25 },
    );
    observer.observe(video);
    return () => observer.disconnect();
  }, [camera.videoUrl]);

  const unavailable = camera.status === "unavailable" || failed;
  const status = STATUS[unavailable ? "unavailable" : playing ? "playing" : "demo"];
  const flagged = events.filter((e) => e.reviewStatus === "pending");

  return (
    <article className="flex flex-col gap-2 rounded-2xl border border-border p-2">
      <button
        type="button"
        onClick={onOpen}
        aria-label={`Open ${camera.name}`}
        className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        {unavailable ? (
          <MediaPlaceholder tone="error" label="Camera unavailable" />
        ) : camera.videoUrl ? (
          <div className="aspect-video overflow-hidden rounded-xl bg-foreground">
            <video
              ref={videoRef}
              src={camera.videoUrl}
              className="size-full object-contain"
              muted
              loop
              playsInline
              preload="none"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onError={() => setFailed(true)}
            />
          </div>
        ) : (
          <MediaPlaceholder label={camera.name} hint="Video placeholder" />
        )}
      </button>

      <div className="flex flex-wrap items-center justify-between gap-2 px-1 pb-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-sm font-bold tabular-nums">{camera.name}</span>
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <span aria-hidden className={`size-2 rounded-full ${status.dot}`} />
            {status.label}
          </span>
        </div>
        {flagged.length > 0 && (
          <a
            href={`#episode-${flagged[0].id}`}
            className="flex shrink-0 items-center gap-1.5 rounded-full bg-surface-muted px-2.5 py-1 text-xs font-semibold hover:bg-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <span aria-hidden className="size-2 rounded-full bg-forte-coral" />
            {flagged.length} flagged
          </a>
        )}
      </div>
    </article>
  );
}

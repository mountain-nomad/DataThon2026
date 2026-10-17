"use client";

import { useImperativeHandle, useRef, useState, type Ref } from "react";
import { formatTimecode } from "@/lib/format";
import { MediaPlaceholder } from "./MediaPlaceholder";

export type VideoMarker = { id: string; sec: number; label: string };
export type VideoPlayerHandle = { seekTo: (sec: number) => void };

// 16:9 frame, object-contain (CCTV footage is never cropped or stretched), custom controls so
// event markers can sit on the timeline. Without `src` it renders a placeholder.
export function VideoPlayer({
  ref,
  src,
  label,
  markers = [],
  onMarkerClick,
  loop = false,
  autoPlay = false,
}: {
  ref?: Ref<VideoPlayerHandle>;
  src?: string;
  label: string;
  markers?: VideoMarker[];
  onMarkerClick?: (id: string) => void;
  loop?: boolean;
  autoPlay?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  const playable = Boolean(src) && failedSrc !== src;

  const seek = (sec: number) => {
    const video = videoRef.current;
    if (!video) return;
    // Before metadata loads the duration is unknown; apply the seek once it is.
    if (video.readyState < 1) {
      pendingSeek.current = sec;
      return;
    }
    video.currentTime = Math.min(Math.max(0, sec), video.duration || sec);
  };

  useImperativeHandle(ref, () => ({ seekTo: seek }), []);

  const toggle = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  };

  return (
    <div className="flex flex-col gap-2">
      {!src ? (
        <MediaPlaceholder label={label} hint="Video placeholder" />
      ) : !playable ? (
        <MediaPlaceholder
          tone="error"
          label="Video failed to load"
          hint="The file may be missing, or the browser can't decode this codec. Serve an MP4/H.264 preview."
        />
      ) : (
        <div className="aspect-video w-full overflow-hidden rounded-xl bg-foreground">
          <video
            ref={videoRef}
            src={src}
            aria-label={label}
            className="size-full object-contain"
            preload="metadata"
            playsInline
            muted={autoPlay}
            autoPlay={autoPlay}
            loop={loop}
            onClick={toggle}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => {
              setDuration(e.currentTarget.duration);
              if (pendingSeek.current !== null) {
                seek(pendingSeek.current);
                pendingSeek.current = null;
              }
            }}
            onError={() => setFailedSrc(src ?? null)}
          />
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggle}
          disabled={!playable}
          aria-label={playing ? "Pause" : "Play"}
          className="flex size-8 shrink-0 items-center justify-center rounded-full border border-border text-foreground transition-colors hover:bg-surface-muted disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {playing ? (
            <svg viewBox="0 0 16 16" className="size-3.5" fill="currentColor" aria-hidden>
              <rect x="3" y="2" width="3.5" height="12" rx="1" />
              <rect x="9.5" y="2" width="3.5" height="12" rx="1" />
            </svg>
          ) : (
            <svg viewBox="0 0 16 16" className="size-3.5" fill="currentColor" aria-hidden>
              <path d="M4 2.5v11a.5.5 0 0 0 .76.43l9-5.5a.5.5 0 0 0 0-.86l-9-5.5A.5.5 0 0 0 4 2.5Z" />
            </svg>
          )}
        </button>

        <div className="relative flex-1">
          {duration > 0 &&
            markers.map((m) => (
              <button
                key={m.id}
                type="button"
                title={`${m.label} · ${formatTimecode(m.sec)}`}
                aria-label={`Jump to ${m.label} at ${formatTimecode(m.sec)}`}
                onClick={() => {
                  seek(m.sec);
                  onMarkerClick?.(m.id);
                }}
                style={{ left: `${(Math.min(m.sec, duration) / duration) * 100}%` }}
                className="absolute -top-2.5 z-10 h-3 w-1 -translate-x-1/2 rounded-full bg-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              />
            ))}
          <input
            type="range"
            aria-label="Seek"
            min={0}
            max={duration || 0}
            step={0.1}
            value={Math.min(time, duration || 0)}
            disabled={!playable || duration === 0}
            onChange={(e) => seek(Number(e.target.value))}
            className="w-full accent-primary disabled:opacity-40"
          />
        </div>

        <span className="shrink-0 text-xs tabular-nums text-muted">
          {formatTimecode(playable ? time : null)} / {formatTimecode(playable ? duration : null)}
        </span>
      </div>
    </div>
  );
}

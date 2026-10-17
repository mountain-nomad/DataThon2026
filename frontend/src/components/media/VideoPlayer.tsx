"use client";

import { useImperativeHandle, useRef, useState, type ReactNode, type Ref } from "react";
import { fmt } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { formatTimecode } from "@/lib/format";
import { MediaPlaceholder } from "./MediaPlaceholder";

export type VideoMarker = { id: string; sec: number; label: string };
export type VideoRange = { id: string; start: number; end: number; label: string; active?: boolean };
export type VideoSegment = { start: number; end: number };
export type VideoPlayerHandle = { seekTo: (sec: number) => void };

// 16:9 frame, object-contain (CCTV footage is never cropped or stretched), custom controls so
// event markers and highlighted ranges can sit on the timeline. Without `src` it renders a
// placeholder. `fallbackSrc` is tried when `src` can't be decoded (e.g. a .mov codec the browser
// lacks); `fallback` replaces the error placeholder when neither plays. `segment` turns the
// player into a clip view of one part of the source: playback and the timeline stay inside it.
export function VideoPlayer({
  ref,
  src,
  fallbackSrc,
  fallback,
  label,
  markers = [],
  onMarkerClick,
  ranges = [],
  onRangeClick,
  segment,
  loop = false,
  autoPlay = false,
}: {
  ref?: Ref<VideoPlayerHandle>;
  src?: string;
  fallbackSrc?: string;
  fallback?: ReactNode;
  label: string;
  markers?: VideoMarker[];
  onMarkerClick?: (id: string) => void;
  ranges?: VideoRange[];
  onRangeClick?: (id: string) => void;
  segment?: VideoSegment;
  loop?: boolean;
  autoPlay?: boolean;
}) {
  const { t } = useI18n();
  const videoRef = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(segment ? segment.start : null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(segment?.start ?? 0);
  const [duration, setDuration] = useState(0);
  const [failed, setFailed] = useState<string[]>([]);

  const current = [src, fallbackSrc].find((s): s is string => Boolean(s) && !failed.includes(s!));
  const playable = current !== undefined;
  const lo = segment ? Math.min(segment.start, duration || segment.start) : 0;
  const hi = segment ? Math.min(segment.end, duration || segment.end) : duration;

  const seek = (sec: number) => {
    const video = videoRef.current;
    if (!video) return;
    // Before metadata loads the duration is unknown; apply the seek once it is.
    if (video.readyState < 1) {
      pendingSeek.current = sec;
      return;
    }
    const max = segment ? Math.min(segment.end, video.duration || segment.end) : video.duration || sec;
    video.currentTime = Math.min(Math.max(segment?.start ?? 0, sec), max);
  };

  useImperativeHandle(ref, () => ({ seekTo: seek }), []);

  const toggle = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      // A finished clip restarts from the beginning of its segment.
      if (segment && video.currentTime >= hi - 0.05) video.currentTime = segment.start;
      video.play().catch(() => {});
    } else video.pause();
  };

  return (
    <div className="flex flex-col gap-2">
      {!src && !fallbackSrc ? (
        <MediaPlaceholder label={label} hint={t.media.videoPlaceholder} />
      ) : !playable ? (
        fallback ?? <MediaPlaceholder
          tone="error"
          label={t.media.videoFailed}
          hint={t.media.videoFailedHint}
        />
      ) : (
        <div className="aspect-video w-full overflow-hidden rounded-xl bg-foreground">
          <video
            ref={videoRef}
            src={current}
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
            onTimeUpdate={(e) => {
              const video = e.currentTarget;
              if (segment && video.currentTime >= segment.end) {
                video.pause();
                video.currentTime = segment.end;
              }
              setTime(video.currentTime);
            }}
            onLoadedMetadata={(e) => {
              setDuration(e.currentTarget.duration);
              if (pendingSeek.current !== null) {
                seek(pendingSeek.current);
                pendingSeek.current = null;
              }
            }}
            onError={() => setFailed((list) => [...list, current!])}
          />
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggle}
          disabled={!playable}
          aria-label={playing ? t.media.pause : t.media.play}
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
            !segment &&
            ranges.map((r) => {
              const start = Math.min(r.start, duration);
              const end = Math.min(Math.max(r.end, r.start), duration);
              return (
                <button
                  key={r.id}
                  type="button"
                  title={`${r.label} · ${formatTimecode(r.start)}–${formatTimecode(r.end)}`}
                  aria-label={fmt(t.media.jumpTo, { label: r.label, time: formatTimecode(r.start) })}
                  aria-pressed={r.active}
                  onClick={() => {
                    seek(r.start);
                    onRangeClick?.(r.id);
                  }}
                  style={{ left: `${(start / duration) * 100}%`, width: `${((end - start) / duration) * 100}%` }}
                  className={`absolute -top-2.5 z-10 h-1.5 min-w-1.5 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                    r.active ? "bg-primary" : "bg-primary/35 hover:bg-primary/60"
                  }`}
                />
              );
            })}
          {duration > 0 &&
            markers.map((m) => (
              <button
                key={m.id}
                type="button"
                title={`${m.label} · ${formatTimecode(m.sec)}`}
                aria-label={fmt(t.media.jumpTo, { label: m.label, time: formatTimecode(m.sec) })}
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
            aria-label={t.media.seek}
            min={lo}
            max={hi || 0}
            step={0.1}
            value={Math.min(Math.max(time, lo), hi || 0)}
            disabled={!playable || duration === 0}
            onChange={(e) => seek(Number(e.target.value))}
            className="w-full accent-primary disabled:opacity-40"
          />
        </div>

        <span className="shrink-0 text-xs tabular-nums text-muted">
          {formatTimecode(playable ? time : null)} / {formatTimecode(playable ? (segment ? hi : duration) : null)}
        </span>
      </div>
    </div>
  );
}

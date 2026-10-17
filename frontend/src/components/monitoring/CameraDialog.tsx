"use client";

import { useEffect, useRef } from "react";
import { VideoPlayer } from "@/components/media/VideoPlayer";
import { MediaPlaceholder } from "@/components/media/MediaPlaceholder";
import { useI18n } from "@/i18n/I18nProvider";
import { formatTimecode } from "@/lib/format";
import type { Camera, ViolationEvent } from "@/lib/types";

// Enlarged view of one camera, on the native <dialog> (focus trap and Esc for free).
export function CameraDialog({
  camera,
  events,
  onClose,
}: {
  camera: Camera | null;
  events: ViolationEvent[];
  onClose: () => void;
}) {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (camera && !dialog.open) dialog.showModal();
    if (!camera && dialog.open) dialog.close();
  }, [camera]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === e.currentTarget && ref.current?.close()}
      className="m-auto w-[min(960px,calc(100vw-32px))] rounded-2xl bg-surface p-0 text-foreground backdrop:bg-foreground/60"
    >
      {camera && (
        <div className="flex flex-col gap-4 p-4 md:p-6">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-xl font-bold">{camera.name}</h2>
            <button
              type="button"
              onClick={() => ref.current?.close()}
              className="rounded-full px-3 py-1 text-sm font-semibold text-muted hover:bg-surface-muted hover:text-foreground"
            >
              {t.dashboard.close}
            </button>
          </div>
          {camera.status === "unavailable" ? (
            <MediaPlaceholder tone="error" label={t.dashboard.cameraUnavailable} />
          ) : (
            <VideoPlayer key={camera.id} src={camera.videoUrl} label={camera.name} loop />
          )}
          {events.length > 0 && (
            <ul className="flex flex-col divide-y divide-border border-t border-border">
              {events.map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-4 py-3 text-sm">
                  <span>
                    <span className="font-semibold">{e.type}</span>
                    <span className="text-muted tabular-nums"> · {formatTimecode(e.timecodeSec)}</span>
                  </span>
                  <a href={`#episode-${e.id}`} onClick={() => ref.current?.close()} className="shrink-0 font-semibold text-primary hover:underline">
                    {t.dashboard.goToEpisode}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </dialog>
  );
}

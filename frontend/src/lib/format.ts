import type { ViolationEvent } from "./types";

export function formatTimecode(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec) || sec < 0) return "--:--";
  const total = Math.floor(sec);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mmss = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return h > 0 ? `${h}:${mmss}` : mmss;
}

export function formatFileSize(bytes: number, locale: string): string {
  const units = ["byte", "kilobyte", "megabyte", "gigabyte"] as const;
  const i = Math.min(units.length - 1, Math.floor(Math.log(Math.max(bytes, 1)) / Math.log(1024)));
  return new Intl.NumberFormat(locale, { style: "unit", unit: units[i], maximumFractionDigits: 1 }).format(
    bytes / 1024 ** i,
  );
}

// Time of the event inside the short clip. Not the jury API's timecode_sec, which is always
// relative to the original recording. Clamped to the clip when its duration is known.
export function episodeTimecodeSec(event: ViolationEvent, clipDurationSec?: number): number | null {
  if (event.clipStartSec === undefined) return null;
  const local = Math.max(0, event.timecodeSec - event.clipStartSec);
  return clipDurationSec ? Math.min(local, clipDurationSec) : local;
}

export function imageSrc(imageBase64: string): string {
  return imageBase64.startsWith("data:") ? imageBase64 : `data:image/jpeg;base64,${imageBase64}`;
}

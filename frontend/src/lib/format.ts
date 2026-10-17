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

export function formatDateTime(iso: string, locale: string): string {
  const date = new Date(iso);
  if (!iso || Number.isNaN(date.getTime())) return "—";
  // Chrome's ICU has no Kazakh date data (it prints "2026 M10 17" or "2026-10-17"), so kk uses
  // the ru numeric format, dd.mm.yyyy, which is also how dates are written in Kazakhstan.
  return new Intl.DateTimeFormat(locale === "kk" ? "ru" : locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function imageSrc(imageBase64: string): string {
  return imageBase64.startsWith("data:") ? imageBase64 : `data:image/jpeg;base64,${imageBase64}`;
}

// mm:ss.d (tenths), for localized violation times: 00:44.2.
export function formatTimecodePrecise(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec) || sec < 0) return "--:--.-";
  const tenths = Math.floor(sec * 10) % 10;
  return `${formatTimecode(sec)}.${tenths}`;
}

// Stand-in for video and images until the real media is added. Keeps the 16:9 frame so the
// layout doesn't shift when the file arrives. `error` is for media that failed or is unavailable.
export function MediaPlaceholder({
  label,
  hint,
  tone = "placeholder",
  className = "",
}: {
  label: string;
  hint?: string;
  tone?: "placeholder" | "error";
  className?: string;
}) {
  const toneClass =
    tone === "error"
      ? "border-danger-fg/20 bg-danger-bg text-danger-fg"
      : "border-dashed border-border bg-surface-muted text-muted";
  return (
    <div
      className={`flex aspect-video w-full flex-col items-center justify-center gap-1 rounded-xl border p-3 text-center ${toneClass} ${className}`}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.06em]">{label}</p>
      {hint && <p className="text-xs">{hint}</p>}
    </div>
  );
}

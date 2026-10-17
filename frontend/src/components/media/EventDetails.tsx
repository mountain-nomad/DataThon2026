import type { RegulatorySource, ReviewStatus } from "@/lib/types";

// Small pieces shared by the inference result cards and the dashboard episode cards.

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

// Never invent a norm: without a confirmed match, say so.
export function RegulatoryReference({ source }: { source?: RegulatorySource }) {
  if (!source) return <span className="text-muted">No confirmed regulatory reference.</span>;
  const text = source.section ? `${source.documentTitle}, ${source.section}` : source.documentTitle;
  return source.url ? (
    <a href={source.url} target="_blank" rel="noreferrer" className="text-primary underline-offset-2 hover:underline">
      {text}
    </a>
  ) : (
    <span>{text}</span>
  );
}

// Keeps "the model flagged this" visibly separate from "a person reviewed this".
export function ReviewBadge({ status }: { status?: ReviewStatus }) {
  if (status === "false_positive") {
    return (
      <span className="inline-flex items-center gap-2 self-start rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted">
        <span aria-hidden className="size-2 rounded-full bg-muted" />
        Human review · False positive
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 self-start rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold">
      <span aria-hidden className="size-2 rounded-full bg-forte-coral" />
      {status === "pending" ? "AI detection · Pending review" : "AI detection"}
    </span>
  );
}

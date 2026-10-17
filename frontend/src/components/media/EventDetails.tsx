"use client";

import { useI18n } from "@/i18n/I18nProvider";
import type { ReviewStatus } from "@/lib/types";

// Small pieces of the dashboard episode cards.

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

// Keeps "the model flagged this" visibly separate from "a person reviewed this".
export function ReviewBadge({ status }: { status?: ReviewStatus }) {
  const { t } = useI18n();
  if (status === "false_positive") {
    return (
      <span className="inline-flex items-center gap-2 self-start rounded-full border border-border px-3 py-1 text-xs font-semibold text-muted">
        <span aria-hidden className="size-2 rounded-full bg-muted" />
        {t.media.badgeFalsePositive}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 self-start rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold">
      <span aria-hidden className="size-2 rounded-full bg-forte-coral" />
      {status === "pending" ? t.media.badgePending : t.media.badgeAi}
    </span>
  );
}

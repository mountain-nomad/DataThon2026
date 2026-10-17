"use client";

import { buttonSecondaryClass } from "@/components/Card";
import { EvidenceFrames } from "@/components/media/EvidenceFrames";
import { Field, RegulatoryReference, ReviewBadge } from "@/components/media/EventDetails";
import { VideoPlayer } from "@/components/media/VideoPlayer";
import { fmt } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { episodeTimecodeSec, formatTimecode } from "@/lib/format";
import type { Camera, ViolationEvent } from "@/lib/types";

export function EpisodeCard({
  event,
  camera,
  onToggleFalsePositive,
}: {
  event: ViolationEvent;
  camera?: Camera;
  onToggleFalsePositive: () => void;
}) {
  const { t } = useI18n();
  const td = t.dashboard;
  const falsePositive = event.reviewStatus === "false_positive";
  const localSec = episodeTimecodeSec(event);

  return (
    <article
      id={`episode-${event.id}`}
      className={`grid scroll-mt-24 gap-6 rounded-2xl border border-border p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:p-6 ${
        falsePositive ? "bg-surface-muted" : "bg-surface"
      }`}
    >
      <VideoPlayer
        src={event.clipUrl}
        label={fmt(td.episodeClip, { camera: camera?.name ?? td.unknownCamera })}
        markers={localSec === null ? [] : [{ id: event.id, sec: localSec, label: event.type }]}
      />

      <div className="flex flex-col gap-4">
        <ReviewBadge status={event.reviewStatus} />
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
            {event.processName ?? td.processUnknown}
          </p>
          <h3 className="text-lg font-bold">{event.type}</h3>
        </div>

        <dl className="grid grid-cols-3 gap-4">
          <Field label={t.fields.camera}>{camera?.name ?? "—"}</Field>
          <Field label={t.fields.episode}>
            <span className="tabular-nums">{formatTimecode(localSec)}</span>
          </Field>
          <Field label={t.fields.source}>
            <span className="tabular-nums">{formatTimecode(event.timecodeSec)}</span>
          </Field>
        </dl>

        <dl className="flex flex-col gap-4">
          <Field label={t.fields.description}>{event.description}</Field>
          <Field label={t.fields.evidence}>
            <EvidenceFrames frames={event.evidenceFrames} />
          </Field>
          <Field label={t.fields.rule}>
            <RegulatoryReference source={event.regulatorySource} />
          </Field>
        </dl>

        <button
          type="button"
          aria-pressed={falsePositive}
          onClick={onToggleFalsePositive}
          className={`${buttonSecondaryClass} self-start`}
        >
          {falsePositive ? td.undoFalse : td.markFalse}
        </button>
      </div>
    </article>
  );
}

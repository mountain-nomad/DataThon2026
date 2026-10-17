"use client";

import { useI18n } from "@/i18n/I18nProvider";
import type { SpecialistResult } from "@/lib/types";
import { EvidenceFrames } from "./EvidenceFrames";
import { MediaPlaceholder } from "./MediaPlaceholder";
import { VideoPlayer } from "./VideoPlayer";

// A localized violation as a clip: the start_sec..end_sec range of the recording, played from the
// recording itself (no cut clip files). Falls back to the first evidence frame when there is no
// localization or the video can't be played.
export function EpisodeMedia({
  result,
  src,
  fallbackSrc,
  label,
}: {
  result: SpecialistResult;
  src?: string;
  fallbackSrc?: string;
  label: string;
}) {
  const { t } = useI18n();
  const { startSec, endSec } = result;
  const frame =
    result.evidenceFrames.length > 0 ? (
      <div className="flex flex-col gap-1">
        <p className="text-xs text-muted">{t.media.episodeFrame}</p>
        <EvidenceFrames frames={result.evidenceFrames} single />
      </div>
    ) : (
      <MediaPlaceholder tone="error" label={t.media.noEpisode} />
    );

  if (startSec === undefined || (!src && !fallbackSrc)) return frame;
  return (
    <VideoPlayer
      src={src}
      fallbackSrc={fallbackSrc}
      fallback={frame}
      label={label}
      segment={{ start: startSec, end: endSec !== undefined && endSec > startSec ? endSec : Infinity }}
    />
  );
}

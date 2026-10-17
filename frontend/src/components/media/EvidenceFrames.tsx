"use client";

import Image from "next/image";
import { useState } from "react";
import { fmt } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";
import { formatTimecode, imageSrc } from "@/lib/format";
import type { EvidenceFrame } from "@/lib/types";
import { MediaPlaceholder } from "./MediaPlaceholder";

function Frame({ frame }: { frame: EvidenceFrame }) {
  const { t } = useI18n();
  const [broken, setBroken] = useState(false);
  const time = formatTimecode(frame.timestampSec);
  return (
    <li className="flex flex-col gap-1">
      {!frame.imageBase64 ? (
        <MediaPlaceholder label={t.media.frame} />
      ) : broken ? (
        <MediaPlaceholder tone="error" label={t.media.frameUnavailable} />
      ) : (
        <div className="relative aspect-video overflow-hidden rounded-xl bg-foreground">
          <Image
            src={imageSrc(frame.imageBase64)}
            alt={fmt(t.media.frameAlt, { time })}
            fill
            unoptimized
            className="object-contain"
            onError={() => setBroken(true)}
          />
        </div>
      )}
      <span className="text-xs tabular-nums text-muted">{time}</span>
    </li>
  );
}

export function EvidenceFrames({ frames }: { frames: EvidenceFrame[] }) {
  const { t } = useI18n();
  if (frames.length === 0) {
    return <p className="text-sm text-muted">{t.media.noFrames}</p>;
  }
  return (
    <ul className="grid grid-cols-3 gap-2">
      {frames.slice(0, 3).map((frame, i) => (
        <Frame key={i} frame={frame} />
      ))}
    </ul>
  );
}

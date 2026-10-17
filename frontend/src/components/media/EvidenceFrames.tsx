"use client";

import Image from "next/image";
import { useState } from "react";
import { formatTimecode, imageSrc } from "@/lib/format";
import type { EvidenceFrame } from "@/lib/types";
import { MediaPlaceholder } from "./MediaPlaceholder";

function Frame({ frame }: { frame: EvidenceFrame }) {
  const [broken, setBroken] = useState(false);
  const time = formatTimecode(frame.timestampSec);
  return (
    <li className="flex flex-col gap-1">
      {!frame.imageBase64 ? (
        <MediaPlaceholder label="Frame" />
      ) : broken ? (
        <MediaPlaceholder tone="error" label="Frame unavailable" />
      ) : (
        <div className="relative aspect-video overflow-hidden rounded-xl bg-foreground">
          <Image
            src={imageSrc(frame.imageBase64)}
            alt={`Evidence frame at ${time}`}
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
  if (frames.length === 0) {
    return <p className="text-sm text-muted">No evidence frame was returned for this event.</p>;
  }
  return (
    <ul className="grid grid-cols-3 gap-2">
      {frames.slice(0, 3).map((frame, i) => (
        <Frame key={i} frame={frame} />
      ))}
    </ul>
  );
}

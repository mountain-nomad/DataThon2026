// Local demo set for /demo-dashboard. Replace with the real prerecorded assets:
//   - camera previews: public/media/cameras/cam-XX.mp4 (light H.264 previews, not originals)
//   - episode clips:   public/media/clips/<event-id>.mp4
// then set videoUrl / clipUrl below. Every statistic on the dashboard is computed from
// DEMO_EVENTS, so there is nothing else to keep in sync.

import type { Camera, ViolationEvent } from "./types";

export const DEMO_CAMERAS: Camera[] = Array.from({ length: 16 }, (_, i) => {
  const n = String(i + 1).padStart(2, "0");
  return {
    id: `cam-${n}`,
    name: `CAM ${n}`,
    videoUrl: undefined, // e.g. `/media/cameras/cam-${n}.mp4`
    // CAM 12 shows the "source unavailable" state.
    status: n === "12" ? "unavailable" : "demo",
  };
});

export const DEMO_EVENTS: ViolationEvent[] = [
  {
    id: "ev-01",
    cameraId: "cam-03",
    processName: "Cash counting",
    type: "Cash counted outside camera view",
    description: "Placeholder. Describe what is visible in the clip and why the model flagged it.",
    timecodeSec: 754,
    clipStartSec: 744,
    evidenceFrames: [
      { timestampSec: 754, imageBase64: "" },
      { timestampSec: 757, imageBase64: "" },
    ],
    reviewStatus: "pending",
  },
  {
    id: "ev-02",
    cameraId: "cam-03",
    processName: "Cash handover",
    type: "Handover without a second employee",
    description: "Placeholder. Describe what is visible in the clip and why the model flagged it.",
    timecodeSec: 1312,
    clipStartSec: 1300,
    evidenceFrames: [{ timestampSec: 1312, imageBase64: "" }],
    regulatorySource: {
      documentTitle: "Document title (placeholder until the reference is confirmed)",
      section: "Section placeholder",
    },
    reviewStatus: "pending",
  },
  {
    id: "ev-03",
    cameraId: "cam-07",
    processName: "Safe operations",
    type: "Safe left open unattended",
    description: "Placeholder. This event has no evidence frame, to show that state.",
    timecodeSec: 302,
    clipStartSec: 290,
    evidenceFrames: [],
    reviewStatus: "pending",
  },
  {
    id: "ev-04",
    cameraId: "cam-11",
    processName: "Cash counting",
    type: "Cash counted outside camera view",
    description: "Placeholder. Already marked as a false positive, to show that state.",
    timecodeSec: 95,
    clipStartSec: 85,
    evidenceFrames: [{ timestampSec: 95, imageBase64: "" }],
    reviewStatus: "false_positive",
  },
  {
    id: "ev-05",
    cameraId: "cam-14",
    processName: "Cash handover",
    type: "Handover without a second employee",
    description: "Placeholder. Describe what is visible in the clip and why the model flagged it.",
    timecodeSec: 2210,
    clipStartSec: 2200,
    evidenceFrames: [
      { timestampSec: 2208, imageBase64: "" },
      { timestampSec: 2210, imageBase64: "" },
      { timestampSec: 2213, imageBase64: "" },
    ],
    reviewStatus: "pending",
  },
];

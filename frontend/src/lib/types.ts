// Frontend data models shared by both demos (frontend_description.md §6).

export type CameraStatus = "demo" | "playing" | "unavailable";

export type Camera = {
  id: string;
  name: string;
  // Undefined until the demo recording is added (a placeholder is shown instead).
  videoUrl?: string;
  status: CameraStatus;
};

export type EvidenceFrame = {
  timestampSec: number;
  // Raw base64 or a data: URI. Empty string = frame not available.
  imageBase64: string;
};

export type RegulatorySource = {
  documentTitle: string;
  section?: string;
  url?: string;
};

export type ReviewStatus = "pending" | "false_positive";

export type ViolationEvent = {
  id: string;
  cameraId?: string;

  processName?: string;
  type: string;
  description: string;

  // Seconds relative to the original video.
  timecodeSec: number;

  // The clip begins at this original-video timestamp.
  clipStartSec?: number;
  clipUrl?: string;

  evidenceFrames: EvidenceFrame[];

  regulatorySource?: RegulatorySource;

  // Human review. Never overwrites the model output above.
  reviewStatus: ReviewStatus;
};

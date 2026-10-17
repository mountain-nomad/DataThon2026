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

// AI pipeline of /demo-inference (frontend_description2.md): router -> specialist -> localization.

// The 7 classes of the scenario router. Canonical ids; names are translated in the dictionaries.
export const SCENARIOS = [
  "ENTRY",
  "COUNTING_DEPOSIT_WITHOUT_CLIENT",
  "CLIENT_CASH_DEPOSIT",
  "COUNTING_FROM_SAFE",
  "OPENING_A_CASH_BAG",
  "RECEIVING_A_BAG_FROM_CLIENT",
  "EXIT_CLOSING",
] as const;
export type ScenarioId = (typeof SCENARIOS)[number];

export type ScenarioResult = {
  // A known id, or the router's raw label if it is outside the 7 classes.
  primary: string;
  secondary?: string;
};

export type SpecialistStatus = "violation" | "no_violation" | "insufficient_evidence";

// One specialist verdict, exactly as returned. Text fields are shown untranslated.
export type SpecialistResult = {
  id: string;
  scenario?: string;
  ruleId?: string;
  status: string;
  quote: string;
  evidence: string;
  // Seconds relative to the original video. Missing until localized.
  startSec?: number;
  endSec?: number;
  evidenceFrames: EvidenceFrame[];
};

export type PipelineResult = {
  scenario: ScenarioResult | null;
  results: SpecialistResult[];
  previewUrl?: string;
};

// The router's own labels (frontend_description2.md §2). Not translated: they are class names.
export const SCENARIO_CODES: Record<ScenarioId, string> = {
  ENTRY: "ENTRY",
  COUNTING_DEPOSIT_WITHOUT_CLIENT: "COUNTING / DEPOSIT WITHOUT CLIENT",
  CLIENT_CASH_DEPOSIT: "CLIENT CASH DEPOSIT",
  COUNTING_FROM_SAFE: "COUNTING FROM SAFE",
  OPENING_A_CASH_BAG: "OPENING A CASH BAG",
  RECEIVING_A_BAG_FROM_CLIENT: "RECEIVING A BAG FROM CLIENT",
  EXIT_CLOSING: "EXIT / CLOSING",
};

export const isScenarioId = (value: string): value is ScenarioId => value in SCENARIO_CODES;

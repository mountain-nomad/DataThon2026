// Frontend data models shared by /demo-inference and /demo-dashboard.

export type EvidenceFrame = {
  timestampSec: number;
  // Raw base64 or a data: URI. Empty string = frame not available.
  imageBase64: string;
};

// Human review of a detected violation. Never overwrites the model output.
export type ReviewStatus = "pending" | "false_positive";

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
  // Position in the backend's specialist_results; addresses the result for review.
  index: number;
  scenario?: string;
  ruleId?: string;
  status: string;
  quote: string;
  evidence: string;
  // Seconds relative to the original video. Missing until localized.
  startSec?: number;
  endSec?: number;
  evidenceFrames: EvidenceFrame[];
  // Only for status "violation".
  reviewStatus?: ReviewStatus;
};

export type PipelineResult = {
  scenario: ScenarioResult | null;
  results: SpecialistResult[];
  previewUrl?: string;
};

// One finished analysis from GET /api/jobs (the source of /demo-dashboard).
export type AnalysisRecord = PipelineResult & {
  jobId: string;
  fileName: string;
  createdAt: string;
  durationSec?: number;
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

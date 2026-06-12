/* ──────────────────────────────────────────────
   SmartPick AI — Domain Types
   ────────────────────────────────────────────── */

// ── Smartphone ──────────────────────────────

export interface SmartphoneSpecs {
  price: number;
  battery_mah: number;
  camera_score: number;
  antutu_score: number;
  storage_gb: number;
  weight_g: number;
  charging_watts: number;
  screen_ratio: number;
}

export interface Smartphone {
  id: string;
  brand: string;
  model_name: string;
  image_url: string;
  supported_by_cv: boolean;
  tech_specs: Record<string, string>;
  default_score?: number;
  specs: SmartphoneSpecs;
}

export interface SmartphoneListResponse {
  smartphones: Smartphone[];
}

// ── Criteria ────────────────────────────────

export interface Criterion {
  id: string;
  name: string;
  direction: string;
  unit: string;
}

export interface CriteriaListResponse {
  criteria: Criterion[];
}

// ── Preferences ─────────────────────────────

export interface PreferencesRequest {
  price: number;
  battery: number;
  camera: number;
  antutu: number;
  storage: number;
  weight: number;
  charging: number;
  screen_ratio: number;
}

export interface PreferencesResponse {
  weights: Record<string, number>;
}

// ── Ranking ─────────────────────────────────

export interface RankingEntry {
  rank: number;
  id: string;
  model_name: string;
  brand: string;
  closeness_coefficient: number;
  score: number;
  s_plus: number;
  s_minus: number;
  weighted_normalized: Record<string, number>;
}

export interface TopMatch {
  rank: number;
  id: string;
  model_name: string;
  brand: string;
  closeness_coefficient: number;
  score: number;
}

export interface RankingResponse {
  method: string;
  ranking_id: string;
  top_match: TopMatch;
  rankings: RankingEntry[];
  weights_used: Record<string, number>;
  ideal_best: Record<string, number>;
  ideal_worst: Record<string, number>;
  criteria_directions: Record<string, string>;
}

// ── Explain ─────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  model_used?: string;
}

export interface ExplainRequest {
  question: string;
  ranking_id: string;
  conversation_history?: ChatMessage[];
}

export interface ExplainResponse {
  answer: string;
  model_used: string;
}

export interface ChatRequest {
  question: string;
  ranking_id?: string;
  conversation_history?: ChatMessage[];
  model?: string;
}

export interface ChatResponse {
  answer: string;
  model_used: string;
}

// ── Detection ───────────────────────────────

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Detection {
  class: string;
  confidence: number;
  bbox: BBox;
}

export interface DetectionResponse {
  detected_object: string;
  model_id: string;
  confidence_score: number;
  action: string;
  detections: Detection[];
  image_width: number;
  image_height: number;
}

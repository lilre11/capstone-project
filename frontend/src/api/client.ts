/* ──────────────────────────────────────────────
   SmartPick AI — API Client
   ────────────────────────────────────────────── */

import axios from 'axios';
import type {
  SmartphoneListResponse,
  CriteriaListResponse,
  PreferencesRequest,
  PreferencesResponse,
  RankingResponse,
  ExplainResponse,
  DetectionResponse,
  ChatMessage,
} from '../types';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

/* ── Detection ─────────────────────────────── */

export async function detectDevice(
  file: File,
  model?: 'model1' | 'model2' | 'model3',
): Promise<DetectionResponse> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<DetectionResponse>('/identify', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params: { backend: 'onnx', model },
  });
  return data;
}

/* ── Smartphones ───────────────────────────── */

export async function getSmartphones(): Promise<SmartphoneListResponse> {
  const { data } = await api.get<SmartphoneListResponse>('/api/smartphones');
  return data;
}

/* ── Criteria ──────────────────────────────── */

export async function getCriteria(): Promise<CriteriaListResponse> {
  const { data } = await api.get<CriteriaListResponse>('/api/criteria');
  return data;
}

/* ── Preferences ───────────────────────────── */

export async function submitPreferences(
  prefs: PreferencesRequest,
): Promise<PreferencesResponse> {
  const { data } = await api.post<PreferencesResponse>('/api/preferences', prefs);
  return data;
}

/* ── Ranking ───────────────────────────────── */

export async function runRanking(
  weights: Record<string, number>,
): Promise<RankingResponse> {
  const { data } = await api.post<RankingResponse>('/api/rank', { weights });
  return data;
}

export async function getRanking(id: string): Promise<RankingResponse> {
  const { data } = await api.get<RankingResponse>(`/api/rank/${id}`);
  return data;
}

/* ── Explain ───────────────────────────────── */

export async function askExplanation(
  question: string,
  rankingId: string,
  conversationHistory?: ChatMessage[],
): Promise<ExplainResponse> {
  const { data } = await api.post<ExplainResponse>('/api/explain', {
    question,
    ranking_id: rankingId,
    conversation_history: conversationHistory,
  });
  return data;
}

export default api;

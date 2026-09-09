// InsightMind AI — Data Science workspace API client.
import { API_BASE } from '../config';
import { jsonRequest, request } from './http';
import type {
  AskResult,
  CleaningApplyResult,
  CleaningHistory,
  CleaningOperation,
  CleaningPreview,
  CleaningRecommendations,
  DatasetOverview,
  DsReport,
  EdaResult,
  PredictionResult,
  QualityReport,
  SessionCreatedResponse,
  SessionSummary,
  TaskDetection,
  TrainResult,
} from '../types/dataScience';

const BASE = '/data-science';

export interface CreateSessionInput {
  columns: string[];
  rows: Record<string, unknown>[];
  name?: string;
  source?: string;
  source_detail?: Record<string, unknown>;
}

export function listSessions() {
  return request<{ sessions: SessionSummary[] }>(`${BASE}/sessions`);
}

export function createSession(input: CreateSessionInput) {
  return jsonRequest<SessionCreatedResponse>(`${BASE}/sessions`, 'POST', input);
}

export function createDemoSession() {
  return jsonRequest<SessionCreatedResponse>(`${BASE}/sessions/demo`, 'POST');
}

export interface UploadDatasetInput {
  name: string;
  content: string; // UTF-8 text for csv/tsv, base64 for xlsx
  format?: 'csv' | 'tsv' | 'xlsx';
  delimiter?: string;
}

export function uploadDataset(input: UploadDatasetInput) {
  return jsonRequest<SessionCreatedResponse>(`${BASE}/sessions/upload`, 'POST', input);
}

export interface FromTableInput {
  connection_id: string;
  table: string;
  db_schema?: string;
  limit?: number;
}

export function createSessionFromTable(input: FromTableInput) {
  return jsonRequest<SessionCreatedResponse>(`${BASE}/sessions/from-table`, 'POST', input);
}

export function getSession(sessionId: string) {
  return request<DatasetOverview>(`${BASE}/sessions/${sessionId}`);
}

export function profileSession(sessionId: string) {
  return jsonRequest<{ dataset: Record<string, unknown>; columns: Record<string, unknown>[] }>(
    `${BASE}/sessions/${sessionId}/profile`,
    'POST',
  );
}

export function analyzeQuality(sessionId: string) {
  return jsonRequest<QualityReport>(`${BASE}/sessions/${sessionId}/quality`, 'POST');
}

export function cleaningRecommendations(sessionId: string) {
  return jsonRequest<CleaningRecommendations>(
    `${BASE}/sessions/${sessionId}/cleaning/recommendations`,
    'POST',
  );
}

export function cleaningPreview(sessionId: string, operations: CleaningOperation[]) {
  return jsonRequest<CleaningPreview>(`${BASE}/sessions/${sessionId}/cleaning/preview`, 'POST', {
    operations,
  });
}

export function cleaningApply(sessionId: string, operations: CleaningOperation[]) {
  return jsonRequest<CleaningApplyResult>(`${BASE}/sessions/${sessionId}/cleaning/apply`, 'POST', {
    operations,
  });
}

export function cleaningUndo(sessionId: string) {
  return jsonRequest<{ history: CleaningHistory; quality: unknown }>(
    `${BASE}/sessions/${sessionId}/cleaning/undo`,
    'POST',
  );
}

export function cleaningReset(sessionId: string) {
  return jsonRequest<{ history: CleaningHistory }>(`${BASE}/sessions/${sessionId}/cleaning/reset`, 'POST');
}

export function runEda(sessionId: string, target?: string | null) {
  return jsonRequest<EdaResult>(`${BASE}/sessions/${sessionId}/eda`, 'POST', { target: target ?? null });
}

export function detectTask(sessionId: string, target: string) {
  return jsonRequest<TaskDetection>(`${BASE}/sessions/${sessionId}/ml/detect-task`, 'POST', { target });
}

export interface TrainInput {
  target: string;
  task?: 'classification' | 'regression';
  models?: string[];
  test_size?: number;
  primary_metric?: string;
  cross_validation?: boolean;
  drop_columns?: string[];
}

export function trainModels(sessionId: string, input: TrainInput) {
  return jsonRequest<TrainResult>(`${BASE}/sessions/${sessionId}/ml/train`, 'POST', input);
}

export function predict(sessionId: string, featureValues: Record<string, unknown>) {
  return jsonRequest<PredictionResult>(`${BASE}/sessions/${sessionId}/ml/predict`, 'POST', {
    feature_values: featureValues,
  });
}

export function generateReport(sessionId: string) {
  return jsonRequest<DsReport>(`${BASE}/sessions/${sessionId}/report`, 'POST');
}

/** Fetches the trained pipeline as a .joblib file and triggers a browser download. */
export async function downloadModel(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}${BASE}/sessions/${sessionId}/ml/model`, {
    credentials: 'include',
  });
  if (!res.ok) {
    let detail = `Download failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body?.error?.message || body?.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || `insightmind-model-${sessionId.slice(0, 8)}.joblib`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function askInsightMind(sessionId: string, question: string) {
  return jsonRequest<AskResult>(`${BASE}/sessions/${sessionId}/ask`, 'POST', { question });
}

// InsightMind AI — Data Science workspace types.
// Response payloads are intentionally loose where the backend returns large,
// deeply-nested analytical objects computed by app.data_science.

export interface DatasetColumnMeta {
  name: string;
  kind: 'numeric' | 'categorical' | 'datetime' | 'boolean' | 'text' | 'empty';
  dtype: string;
  missing: number;
}

export interface DatasetOverview {
  name: string;
  source: string;
  source_detail: Record<string, unknown>;
  n_rows: number;
  n_cols: number;
  sampled: boolean;
  original_row_count: number | null;
  columns: DatasetColumnMeta[];
  sample_rows: Record<string, unknown>[];
  cleaning_steps?: number;
  has_model?: boolean;
}

export interface SessionCreatedResponse {
  session_id: string;
  dataset: DatasetOverview;
}

export interface SessionSummary {
  session_id: string;
  name: string;
  source: string;
  n_rows: number;
  n_cols: number;
  cleaning_steps: number;
  has_model: boolean;
  created_at: number;
  last_seen: number;
}

export interface QualityDimension {
  key: string;
  label: string;
  score: number;
  issues: string[];
}

export interface QualityScore {
  overall: number;
  grade: string;
  dimensions: QualityDimension[];
}

export interface QualityIssue {
  code: string;
  dimension: string;
  severity: 'info' | 'low' | 'medium' | 'high';
  title: string;
  columns: string[];
  evidence: Record<string, unknown>;
  recommendation: string;
  suggested_operation: CleaningOperation | null;
}

export interface QualityReport {
  score: QualityScore;
  issue_count: number;
  issues: QualityIssue[];
  narrative?: string | null;
}

export interface CleaningOperation {
  op: string;
  params: Record<string, unknown>;
}

export interface CleaningRecommendation {
  id: string;
  issue: string;
  problem: string;
  operation: CleaningOperation;
  solution: string;
  reason: string;
  expected_impact: string;
  risk: 'low' | 'medium' | 'high';
}

export interface CleaningRecommendations {
  recommendations: CleaningRecommendation[];
  safe_fix_count: number;
  review_count: number;
}

export interface FrameStats {
  rows: number;
  columns: number;
  missing_cells: number;
  duplicate_rows: number;
}

export interface CleaningColumnDiff {
  column: string;
  status: 'unchanged' | 'modified' | 'dropped' | 'added';
  missing_before: number | null;
  missing_after: number | null;
  dtype_before: string | null;
  dtype_after: string | null;
  action: string;
}

export interface CleaningPreview {
  before: FrameStats;
  after: FrameStats;
  column_diff: CleaningColumnDiff[];
  operation_records: Record<string, unknown>[];
}

export interface CleaningHistoryStep {
  index: number;
  operations: CleaningOperation[];
  records: Record<string, unknown>[];
  rows_before: number;
  rows_after: number;
  cols_before: number;
  cols_after: number;
}

export interface CleaningHistory {
  steps: CleaningHistoryStep[];
  original: FrameStats;
  current: FrameStats;
  total_operations: number;
}

export interface CleaningApplyResult {
  step: CleaningHistoryStep;
  current: FrameStats;
  history: CleaningHistory;
  quality_before: QualityScore;
  quality_after: QualityScore;
  narrative?: string | null;
}

export interface EdaChart {
  kind: 'histogram' | 'box' | 'bar' | 'pie' | 'scatter' | 'line' | 'correlation_heatmap';
  title: string;
  column?: string;
  x?: string;
  y?: string;
  data: unknown;
}

export interface EdaInsight {
  category: string;
  text: string;
  evidence: Record<string, unknown>;
}

export interface EdaResult {
  target: string | null;
  numeric_summary: Record<string, unknown>[];
  categorical_summary: Record<string, unknown>[];
  correlations: {
    columns: string[];
    matrix: (number | null)[][];
    top_pairs: { a: string; b: string; corr: number }[];
  } | null;
  charts: EdaChart[];
  insights: EdaInsight[];
  narrative?: string | null;
}

export interface TaskDetection {
  target: string;
  detected_task: 'classification' | 'regression';
  target_kind: string;
  unique_values: number;
  missing: number;
  class_distribution?: Record<string, number>;
  is_imbalanced?: boolean;
  default_primary_metric: string;
  target_stats?: Record<string, number>;
}

export interface ModelComparisonRow {
  model: string;
  is_best?: boolean;
  primary_metric?: string;
  primary_score?: number | null;
  error?: string;
  [metric: string]: unknown;
}

export interface FeatureImportance {
  method: string;
  feature: string;
  importance: number;
  raw: number;
}

export interface FeatureSchemaEntry {
  name: string;
  type: 'number' | 'category';
  min?: number | null;
  max?: number | null;
  median?: number | null;
  options?: (string | number)[];
}

export interface TrainResult {
  task: 'classification' | 'regression';
  target: string;
  primary_metric: string;
  best_model_name: string;
  comparison: ModelComparisonRow[];
  metrics: Record<string, unknown>;
  feature_importance: FeatureImportance[];
  feature_schema: FeatureSchemaEntry[];
  label_classes: (string | number)[] | null;
  n_train: number;
  n_test: number;
  warnings: string[];
  narrative?: string | null;
}

export interface PredictionResult {
  prediction: string | number;
  probabilities?: Record<string, number>;
  confidence?: number;
}

export interface DsReportSection {
  id: string;
  title: string;
  body: Record<string, unknown>;
}

export interface DsReport {
  generated_at: string;
  title: string;
  executive_summary: string;
  sections: DsReportSection[];
  recommendations: string[];
}

export interface AskResult {
  answer: string;
  grounded: boolean;
  llm_available: boolean;
}

export type WorkspaceStep = 'dataset' | 'quality' | 'clean' | 'explore' | 'ml' | 'report';

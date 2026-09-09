import { useEffect, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, ErrorBlock, LoadingBlock, Panel, Pill, num } from './ui';
import { detectTask, predict, trainModels } from '../../services/dataScience';
import type {
  DatasetOverview,
  PredictionResult,
  TaskDetection,
  TrainResult,
  WorkspaceStep,
} from '../../types/dataScience';

const CLS_METRICS = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc'];
const REG_METRICS = ['r2', 'mae', 'rmse', 'mse'];
const METRIC_LABEL: Record<string, string> = {
  accuracy: 'Accuracy', precision: 'Precision', recall: 'Recall', f1: 'F1', roc_auc: 'ROC-AUC',
  r2: 'R²', mae: 'MAE', rmse: 'RMSE', mse: 'MSE',
};

export function MlStep({
  sessionId,
  dataset,
  target,
  onTargetChange,
  onResult,
  onGoto,
}: {
  sessionId: string;
  dataset: DatasetOverview;
  target: string | null;
  onTargetChange: (t: string) => void;
  onResult: (r: TrainResult) => void;
  onGoto: (step: WorkspaceStep) => void;
}) {
  const [detection, setDetection] = useState<TaskDetection | null>(null);
  const [taskOverride, setTaskOverride] = useState<'classification' | 'regression' | ''>('');
  const [primaryMetric, setPrimaryMetric] = useState<string>('');
  const [testSize, setTestSize] = useState(0.2);
  const [cv, setCv] = useState(true);
  const [result, setResult] = useState<TrainResult | null>(null);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDetection(null);
    setResult(null);
    if (!target) return;
    detectTask(sessionId, target)
      .then(setDetection)
      .catch((err) => setError(err instanceof Error ? err.message : 'Task detection failed'));
  }, [sessionId, target]);

  const effectiveTask = taskOverride || detection?.detected_task;
  const metrics = effectiveTask === 'regression' ? REG_METRICS : CLS_METRICS;

  const runTrain = async () => {
    if (!target) return;
    setTraining(true);
    setError(null);
    try {
      const res = await trainModels(sessionId, {
        target,
        task: taskOverride || undefined,
        primary_metric: primaryMetric || undefined,
        test_size: testSize,
        cross_validation: cv,
      });
      setResult(res);
      onResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  return (
    <div>
      <Panel
        title="Machine Learning"
        subtitle="Models are really trained on the current dataset. Preprocessing is fitted on the training split only — no leakage."
        actions={
          <select
            value={target ?? ''}
            onChange={(e) => onTargetChange(e.target.value)}
            style={{ padding: '8px 10px', border: `1.5px solid ${T.border2}`, fontFamily: T.fontMono, fontSize: '0.72rem', background: '#fff' }}
          >
            <option value="">Select target column…</option>
            {dataset.columns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        }
      >
        {!target ? (
          <div style={{ padding: 24, textAlign: 'center', color: T.text3, fontSize: '0.85rem' }}>
            Pick the column you want to predict.
          </div>
        ) : (
          <>
            {detection && (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
                <Pill color={T.accent}>detected: {detection.detected_task}</Pill>
                <span style={{ fontSize: '0.78rem', color: T.text3 }}>
                  {detection.unique_values} unique · {detection.missing} missing
                  {detection.is_imbalanced ? ' · imbalanced' : ''}
                </span>
                {detection.class_distribution && (
                  <span style={{ fontFamily: T.fontMono, fontSize: '0.68rem', color: T.text3 }}>
                    {Object.entries(detection.class_distribution).map(([k, v]) => `${k}:${v}`).join('  ')}
                  </span>
                )}
              </div>
            )}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <Field label="Task">
                <select value={taskOverride} onChange={(e) => setTaskOverride(e.target.value as 'classification' | 'regression' | '')} style={selectStyle}>
                  <option value="">auto ({detection?.detected_task ?? '…'})</option>
                  <option value="classification">classification</option>
                  <option value="regression">regression</option>
                </select>
              </Field>
              <Field label="Primary metric">
                <select value={primaryMetric} onChange={(e) => setPrimaryMetric(e.target.value)} style={selectStyle}>
                  <option value="">auto ({detection?.default_primary_metric ?? '…'})</option>
                  {metrics.map((m) => (
                    <option key={m} value={m}>
                      {METRIC_LABEL[m]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Test split">
                <select value={testSize} onChange={(e) => setTestSize(Number(e.target.value))} style={selectStyle}>
                  <option value={0.1}>90 / 10</option>
                  <option value={0.2}>80 / 20</option>
                  <option value={0.3}>70 / 30</option>
                </select>
              </Field>
              <Field label="Cross-validation">
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.76rem' }}>
                  <input type="checkbox" checked={cv} onChange={(e) => setCv(e.target.checked)} /> 5-fold
                </label>
              </Field>
              <Btn onClick={runTrain} disabled={training}>
                {training ? 'Training…' : 'Train & compare'}
              </Btn>
            </div>
          </>
        )}
        {error && <div style={{ marginTop: 12 }}><ErrorBlock message={error} onRetry={() => setError(null)} /></div>}
      </Panel>

      {training && <LoadingBlock label="Training models — logistic regression, trees, forests, boosting…" />}

      {result && (
        <>
          <Panel title="Best model">
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
              <div>
                <div style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900, fontSize: '1.8rem', color: T.text }}>
                  {result.best_model_name}
                </div>
                <div style={{ fontFamily: T.fontMono, fontSize: '0.68rem', color: T.text3, textTransform: 'uppercase' }}>
                  {result.task} · target {result.target} · {num(result.n_train)} train / {num(result.n_test)} test
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900, fontSize: '2rem', color: T.green }}>
                  {num(result.metrics[result.primary_metric], 3)}
                </div>
                <div style={{ fontFamily: T.fontMono, fontSize: '0.64rem', color: T.text3, textTransform: 'uppercase' }}>
                  {METRIC_LABEL[result.primary_metric] || result.primary_metric}
                </div>
              </div>
            </div>
            {result.warnings.length > 0 && (
              <ul style={{ margin: '14px 0 0', paddingLeft: 18, color: T.orange, fontSize: '0.76rem' }}>
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
            {result.narrative && (
              <p style={{ marginTop: 14, padding: 14, background: T.bg, borderLeft: `3px solid ${T.accent}`, fontSize: '0.82rem', lineHeight: 1.7, color: T.text2 }}>
                {result.narrative}
              </p>
            )}
          </Panel>

          <Panel title="Model comparison" subtitle={`Ranked by ${METRIC_LABEL[result.primary_metric] || result.primary_metric}. Best is highlighted.`}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: T.text3, fontFamily: T.fontMono, fontSize: '0.62rem', textTransform: 'uppercase' }}>
                    <th style={{ padding: '6px 10px' }}>Model</th>
                    {metrics.map((m) => (
                      <th key={m} style={{ padding: '6px 10px' }}>
                        {METRIC_LABEL[m]}
                      </th>
                    ))}
                    <th style={{ padding: '6px 10px' }}>CV mean</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparison.map((row) => (
                    <tr
                      key={row.model}
                      style={{
                        borderTop: '1px solid rgba(0,0,0,0.06)',
                        background: row.is_best ? T.greenDim : undefined,
                        fontWeight: row.is_best ? 700 : 400,
                      }}
                    >
                      <td style={{ padding: '6px 10px' }}>
                        {row.model} {row.is_best ? <Pill color={T.green}>best</Pill> : null}
                      </td>
                      {row.error
                        ? <td colSpan={metrics.length + 1} style={{ padding: '6px 10px', color: T.red }}>{row.error}</td>
                        : (
                          <>
                            {metrics.map((m) => (
                              <td key={m} style={{ padding: '6px 10px' }}>
                                {num(row[m], 3)}
                              </td>
                            ))}
                            <td style={{ padding: '6px 10px' }}>{row.cv_mean !== undefined ? num(row.cv_mean, 3) : '—'}</td>
                          </>
                        )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Feature importance" subtitle={`Method: ${result.feature_importance[0]?.method ?? 'n/a'}. One-hot columns collapsed to their source feature.`}>
            <div style={{ display: 'grid', gap: 6 }}>
              {result.feature_importance.map((f) => (
                <div key={f.feature} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ width: 180, fontSize: '0.76rem', color: T.text2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {f.feature}
                  </span>
                  <div style={{ flex: 1, height: 10, background: T.s3 }}>
                    <div style={{ width: `${Math.min(Math.abs(f.importance) * 100, 100)}%`, height: '100%', background: T.purple }} />
                  </div>
                  <span style={{ width: 52, textAlign: 'right', fontFamily: T.fontMono, fontSize: '0.7rem', color: T.text3 }}>
                    {(f.importance * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </Panel>

          <PredictionPanel sessionId={sessionId} result={result} />

          <div style={{ display: 'flex', gap: 8 }}>
            <Btn small onClick={() => onGoto('report')}>Generate report</Btn>
          </div>
        </>
      )}
    </div>
  );
}

function PredictionPanel({ sessionId, result }: { sessionId: string; result: TrainResult }) {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    result.feature_schema.forEach((s) => {
      init[s.name] = s.type === 'number' ? String(s.median ?? '') : String(s.options?.[0] ?? '');
    });
    return init;
  });
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {};
      result.feature_schema.forEach((s) => {
        const raw = values[s.name];
        payload[s.name] = s.type === 'number' ? (raw === '' ? null : Number(raw)) : raw;
      });
      setPrediction(await predict(sessionId, payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Make a prediction" subtitle="Inputs run through the exact training pipeline.">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
        {result.feature_schema.map((s) => (
          <Field key={s.name} label={s.name}>
            {s.type === 'category' && s.options ? (
              <select value={values[s.name]} onChange={(e) => setValues({ ...values, [s.name]: e.target.value })} style={selectStyle}>
                {s.options.map((o) => (
                  <option key={String(o)} value={String(o)}>
                    {String(o)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="number"
                value={values[s.name]}
                onChange={(e) => setValues({ ...values, [s.name]: e.target.value })}
                placeholder={s.median !== undefined && s.median !== null ? `median ${num(s.median)}` : ''}
                style={selectStyle}
              />
            )}
          </Field>
        ))}
      </div>
      <div style={{ marginTop: 14, display: 'flex', gap: 12, alignItems: 'center' }}>
        <Btn small onClick={run} disabled={busy}>
          {busy ? 'Predicting…' : 'Predict'}
        </Btn>
        {prediction && (
          <div style={{ fontSize: '0.85rem' }}>
            <span style={{ color: T.text3 }}>Prediction: </span>
            <strong style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontSize: '1.1rem', color: T.green }}>
              {typeof prediction.prediction === 'number' ? num(prediction.prediction) : String(prediction.prediction)}
            </strong>
            {prediction.confidence !== undefined && (
              <span style={{ color: T.text3, marginLeft: 10, fontFamily: T.fontMono, fontSize: '0.72rem' }}>
                {(prediction.confidence * 100).toFixed(1)}% confidence
              </span>
            )}
          </div>
        )}
      </div>
      {error && <div style={{ marginTop: 10 }}><ErrorBlock message={error} /></div>}
    </Panel>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontFamily: T.fontMono, fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: T.text3 }}>
        {label}
      </span>
      {children}
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: `1.5px solid ${T.border2}`,
  fontFamily: T.fontMono,
  fontSize: '0.72rem',
  background: '#fff',
  width: '100%',
};

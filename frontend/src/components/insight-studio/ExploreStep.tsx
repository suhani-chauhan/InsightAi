import { useEffect, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, ErrorBlock, LoadingBlock, Panel, Pill, num } from './ui';
import { DsChart } from './DsChart';
import { PinToDashboardButton } from './PinToDashboardButton';
import { runEda } from '../../services/dataScience';
import type { DatasetOverview, EdaResult, WorkspaceStep } from '../../types/dataScience';

const CATEGORY_COLOR: Record<string, string> = {
  statistical: T.accent,
  data_quality: T.orange,
  business: T.green,
  ml: T.purple,
};

export function ExploreStep({
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
  onTargetChange: (t: string | null) => void;
  onResult: (r: EdaResult) => void;
  onGoto: (step: WorkspaceStep) => void;
}) {
  const [eda, setEda] = useState<EdaResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    runEda(sessionId, target)
      .then((res) => {
        setEda(res);
        onResult(res);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'EDA failed'))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [sessionId, target]);

  return (
    <div>
      <Panel
        title="Exploratory Analysis"
        subtitle="Statistics and charts computed with pandas / numpy. Insights are grounded in those computations."
        actions={
          <>
            <select
              value={target ?? ''}
              onChange={(e) => onTargetChange(e.target.value || null)}
              style={{
                padding: '8px 10px',
                border: `1.5px solid ${T.border2}`,
                fontFamily: T.fontMono,
                fontSize: '0.72rem',
                background: '#fff',
              }}
            >
              <option value="">No target column</option>
              {dataset.columns.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
            <Btn small onClick={() => onGoto('ml')}>
              Build model
            </Btn>
          </>
        }
      >
        {loading && !eda ? (
          <LoadingBlock label="Running exploratory analysis…" />
        ) : error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : eda ? (
          <>
            {eda.narrative && (
              <p style={{ padding: 14, background: T.bg, borderLeft: `3px solid ${T.accent}`, fontSize: '0.82rem', lineHeight: 1.7, color: T.text2, marginBottom: 16 }}>
                {eda.narrative}
              </p>
            )}
            <div style={{ display: 'grid', gap: 10 }}>
              {eda.insights.map((ins, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: '0.82rem', color: T.text2, lineHeight: 1.6 }}>
                  <Pill color={CATEGORY_COLOR[ins.category] || T.text3}>{ins.category.replace('_', ' ')}</Pill>
                  <span>{ins.text}</span>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </Panel>

      {eda && eda.numeric_summary.length > 0 && (
        <Panel
          title="Numeric summary"
          actions={
            <PinToDashboardButton
              title="Numeric summary"
              vizType="table"
              columns={['column', 'mean', 'median', 'std', 'min', 'max', 'skew']}
              rows={eda.numeric_summary.map((r) => {
                const s = r as Record<string, unknown>;
                return {
                  column: String(s.column),
                  mean: s.mean ?? null,
                  median: s.median ?? null,
                  std: s.std ?? null,
                  min: s.min ?? null,
                  max: s.max ?? null,
                  skew: s.skew ?? null,
                };
              })}
              size="full"
            />
          }
        >
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: T.text3, fontFamily: T.fontMono, fontSize: '0.62rem', textTransform: 'uppercase' }}>
                  {['Column', 'Count', 'Mean', 'Median', 'Std', 'Min', 'Max', 'Skew'].map((h) => (
                    <th key={h} style={{ padding: '6px 10px' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {eda.numeric_summary.map((row, i) => {
                  const r = row as Record<string, unknown>;
                  return (
                    <tr key={i} style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                      <td style={{ padding: '6px 10px', fontWeight: 700 }}>{String(r.column)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.count)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.mean)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.median)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.std)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.min)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.max)}</td>
                      <td style={{ padding: '6px 10px' }}>{num(r.skew)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {eda && eda.charts.length > 0 && (
        <Panel title={`Charts (${eda.charts.length})`}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 14 }}>
            {eda.charts.map((chart, i) => (
              <DsChart key={i} chart={chart} />
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

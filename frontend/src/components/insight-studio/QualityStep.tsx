import { useEffect, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, ErrorBlock, LoadingBlock, Panel, Pill, gradeColor, severityColor } from './ui';
import { analyzeQuality } from '../../services/dataScience';
import type { QualityReport, WorkspaceStep } from '../../types/dataScience';

export function QualityStep({
  sessionId,
  onReport,
  onGoto,
}: {
  sessionId: string;
  onReport: (report: QualityReport) => void;
  onGoto: (step: WorkspaceStep) => void;
}) {
  const [report, setReport] = useState<QualityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    analyzeQuality(sessionId)
      .then((res) => {
        setReport(res);
        onReport(res);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to analyse quality'))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [sessionId]);

  if (loading && !report) return <LoadingBlock label="Analysing data quality…" />;
  if (error) return <ErrorBlock message={error} onRetry={load} />;
  if (!report) return null;

  const { score } = report;

  return (
    <div>
      <Panel
        title="Data Quality Score"
        subtitle="Deterministic: each dimension starts at 100 and loses points per issue, weighted by severity."
        actions={<Btn small onClick={() => onGoto('clean')}>Fix issues</Btn>}
      >
        <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                fontFamily: T.fontHead,
                fontStyle: 'italic',
                fontWeight: 900,
                fontSize: '3.4rem',
                lineHeight: 1,
                color: gradeColor[score.grade] || T.text,
              }}
            >
              {score.overall}
            </div>
            <div style={{ fontFamily: T.fontMono, fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: T.text3 }}>
              / 100 · {score.grade}
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 260, display: 'grid', gap: 8 }}>
            {score.dimensions.map((dim) => (
              <div key={dim.key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ width: 150, fontSize: '0.72rem', color: T.text2 }}>{dim.label}</span>
                <div style={{ flex: 1, height: 8, background: T.s3 }}>
                  <div
                    style={{
                      width: `${dim.score}%`,
                      height: '100%',
                      background: dim.score >= 85 ? T.green : dim.score >= 65 ? T.yellow : T.red,
                    }}
                  />
                </div>
                <span style={{ width: 38, textAlign: 'right', fontFamily: T.fontMono, fontSize: '0.7rem', color: T.text3 }}>
                  {dim.score}
                </span>
              </div>
            ))}
          </div>
        </div>
        {report.narrative && (
          <p style={{ marginTop: 18, padding: 14, background: T.bg, borderLeft: `3px solid ${T.accent}`, fontSize: '0.82rem', lineHeight: 1.7, color: T.text2 }}>
            {report.narrative}
          </p>
        )}
      </Panel>

      <Panel title={`Issues (${report.issue_count})`} subtitle="Most severe first. Every figure is computed, not estimated.">
        <div style={{ display: 'grid', gap: 10 }}>
          {report.issues.map((issue) => (
            <div key={issue.code} style={{ border: '1px solid rgba(0,0,0,0.08)', padding: '14px 16px', background: '#fff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
                <Pill color={severityColor[issue.severity]}>{issue.severity}</Pill>
                <strong style={{ fontSize: '0.86rem' }}>{issue.title}</strong>
                {issue.columns.map((c) => (
                  <code key={c} style={{ fontFamily: T.fontMono, fontSize: '0.7rem', color: T.text3 }}>
                    {c}
                  </code>
                ))}
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: T.text2, lineHeight: 1.6 }}>{issue.recommendation}</p>
              <div style={{ marginTop: 8, fontFamily: T.fontMono, fontSize: '0.66rem', color: T.text3 }}>
                {Object.entries(issue.evidence)
                  .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
                  .join('  ·  ')}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

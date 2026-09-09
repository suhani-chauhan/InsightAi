import { useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, ErrorBlock, LoadingBlock, Panel } from './ui';
import { generateReport } from '../../services/dataScience';
import type { DsReport } from '../../types/dataScience';

export function ReportStep({ sessionId }: { sessionId: string }) {
  const [report, setReport] = useState<DsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    generateReport(sessionId)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : 'Report generation failed'))
      .finally(() => setLoading(false));
  };

  const download = () => {
    if (!report) return;
    const html = renderReportHtml(report);
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insightmind-report-${sessionId.slice(0, 8)}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <Panel
        title="Data Science Report"
        subtitle="Assembled from the computed artifacts on this session — dataset, quality, cleaning, EDA and ML."
        actions={
          <>
            <Btn small variant="ghost" onClick={load} disabled={loading}>
              {loading ? 'Generating…' : report ? 'Regenerate' : 'Generate'}
            </Btn>
            {report && (
              <Btn small onClick={download}>
                Download HTML
              </Btn>
            )}
          </>
        }
      >
        {loading && !report ? (
          <LoadingBlock label="Assembling report…" />
        ) : error ? (
          <ErrorBlock message={error} onRetry={load} />
        ) : !report ? (
          <div style={{ padding: 24, textAlign: 'center', color: T.text3, fontSize: '0.85rem' }}>
            Run the earlier steps, then generate the report.
          </div>
        ) : (
          <>
            <p style={{ fontSize: '0.88rem', lineHeight: 1.8, color: T.text2 }}>{report.executive_summary}</p>
            <div style={{ marginTop: 10, fontFamily: T.fontMono, fontSize: '0.66rem', color: T.text3 }}>
              generated {new Date(report.generated_at).toLocaleString()}
            </div>
          </>
        )}
      </Panel>

      {report?.sections.map((section) => (
        <Panel key={section.id} title={section.title}>
          <SectionBody id={section.id} body={section.body} />
        </Panel>
      ))}

      {report && report.recommendations.length > 0 && (
        <Panel title="Recommendations">
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.85rem', lineHeight: 1.8, color: T.text2 }}>
            {report.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

type Body = Record<string, unknown>;

function SectionBody({ id, body }: { id: string; body: Body }) {
  if (id === 'overview') return <KeyValues obj={pick(body, ['name', 'rows', 'columns', 'sampled', 'column_kinds'])} />;

  if (id === 'quality') {
    const dims = (body.dimensions as { label: string; score: number }[]) || [];
    const issues = (body.top_issues as { title: string; severity: string; recommendation: string }[]) || [];
    return (
      <div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 14 }}>
          <Stat label="Overall" value={`${body.overall_score ?? '—'} / 100`} />
          <Stat label="Grade" value={String(body.grade ?? '—')} />
          <Stat label="Issues" value={String(body.issue_count ?? 0)} />
        </div>
        <MiniTable
          head={['Dimension', 'Score']}
          rows={dims.map((d) => [d.label, String(d.score)])}
        />
        {issues.length > 0 && (
          <ul style={listStyle}>
            {issues.map((i, k) => (
              <li key={k}>
                <strong>[{i.severity}]</strong> {i.title} — {i.recommendation}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (id === 'cleaning') {
    const ops = (body.operations as { action?: string; op?: string }[]) || [];
    const before = (body.before as Body) || {};
    const after = (body.after as Body) || {};
    return (
      <div>
        <MiniTable
          head={['', 'Before', 'After']}
          rows={[
            ['Rows', String(before.rows ?? '—'), String(after.rows ?? '—')],
            ['Missing cells', String(before.missing_cells ?? '—'), String(after.missing_cells ?? '—')],
            ['Duplicate rows', String(before.duplicate_rows ?? '—'), String(after.duplicate_rows ?? '—')],
          ]}
        />
        <ul style={listStyle}>
          {ops.map((o, k) => (
            <li key={k}>{o.action || o.op}</li>
          ))}
        </ul>
      </div>
    );
  }

  if (id === 'eda') {
    const insights = (body.insights as { category: string; text: string }[]) || [];
    const corr = (body.top_correlations as { a: string; b: string; corr: number }[]) || [];
    return (
      <div>
        <ul style={listStyle}>
          {insights.map((i, k) => (
            <li key={k}>
              <strong>{i.category}:</strong> {i.text}
            </li>
          ))}
        </ul>
        {corr.length > 0 && (
          <MiniTable
            head={['Pair', 'r']}
            rows={corr.map((c) => [`${c.a} ↔ ${c.b}`, c.corr.toFixed(2)])}
          />
        )}
      </div>
    );
  }

  if (id === 'ml') {
    const cmp = (body.comparison as Record<string, unknown>[]) || [];
    const fi = (body.feature_importance as { feature: string; importance: number }[]) || [];
    const metricKeys = cmp.length
      ? Object.keys(cmp[0]).filter((k) => typeof cmp[0][k] === 'number' && !['is_best', 'primary_score'].includes(k))
      : [];
    return (
      <div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 14 }}>
          <Stat label="Task" value={String(body.task ?? '—')} />
          <Stat label="Target" value={String(body.target ?? '—')} />
          <Stat label="Best model" value={String(body.best_model ?? '—')} />
          <Stat label={String(body.primary_metric ?? 'metric')} value={fmtMetric((body.metrics as Body)?.[String(body.primary_metric)])} />
        </div>
        <MiniTable
          head={['Model', ...metricKeys]}
          rows={cmp.map((r) => [String(r.model), ...metricKeys.map((k) => fmtMetric(r[k]))])}
        />
        {fi.length > 0 && (
          <MiniTable
            head={['Feature', 'Importance']}
            rows={fi.map((f) => [f.feature, `${(f.importance * 100).toFixed(1)}%`])}
          />
        )}
      </div>
    );
  }

  return <KeyValues obj={body} />;
}

function pick(obj: Body, keys: string[]): Body {
  return Object.fromEntries(keys.filter((k) => k in obj).map((k) => [k, obj[k]]));
}

function fmtMetric(v: unknown): string {
  if (typeof v !== 'number') return v == null ? '—' : String(v);
  return Number.isInteger(v) ? String(v) : v.toFixed(3);
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontFamily: T.fontMono, fontSize: '0.6rem', textTransform: 'uppercase', color: T.text3 }}>{label}</div>
      <div style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900, fontSize: '1.1rem' }}>{value}</div>
    </div>
  );
}

function KeyValues({ obj }: { obj: Body }) {
  return (
    <MiniTable
      head={['Field', 'Value']}
      rows={Object.entries(obj).map(([k, v]) => [k, typeof v === 'object' ? JSON.stringify(v) : String(v)])}
    />
  );
}

function MiniTable({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div style={{ overflowX: 'auto', marginTop: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', color: T.text3, fontFamily: T.fontMono, fontSize: '0.62rem', textTransform: 'uppercase' }}>
            {head.map((h, i) => (
              <th key={i} style={{ padding: '6px 10px' }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
              {r.map((c, j) => (
                <td key={j} style={{ padding: '6px 10px', color: j === 0 ? T.text : T.text2, fontWeight: j === 0 ? 700 : 400 }}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const listStyle: React.CSSProperties = {
  margin: '12px 0 0',
  paddingLeft: 18,
  fontSize: '0.82rem',
  lineHeight: 1.8,
  color: T.text2,
};

function renderReportHtml(report: DsReport): string {
  const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c] as string);
  const sections = report.sections
    .map(
      (s) =>
        `<section><h2>${esc(s.title)}</h2><pre>${esc(JSON.stringify(s.body, null, 2))}</pre></section>`,
    )
    .join('\n');
  const recs = report.recommendations.map((r) => `<li>${esc(r)}</li>`).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(report.title)}</title>
<style>body{font-family:Georgia,serif;max-width:900px;margin:40px auto;padding:0 20px;color:#1a1a1a;line-height:1.7}
h1{font-style:italic}h2{border-bottom:2px solid #1a1a1a;padding-bottom:4px;margin-top:36px}
pre{background:#f6f3ed;padding:14px;overflow-x:auto;font-size:12px;white-space:pre-wrap}
.summary{background:#f6f3ed;padding:18px;border-left:4px solid #0ea5e9}</style></head>
<body><h1>${esc(report.title)}</h1>
<p class="summary">${esc(report.executive_summary)}</p>
<p><small>Generated ${esc(report.generated_at)} · InsightMind AI</small></p>
${sections}
<section><h2>Recommendations</h2><ul>${recs}</ul></section>
</body></html>`;
}

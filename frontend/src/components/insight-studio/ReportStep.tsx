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
          <pre
            style={{
              margin: 0,
              padding: 16,
              background: T.bg,
              border: '1px solid rgba(0,0,0,0.06)',
              fontFamily: T.fontMono,
              fontSize: '0.72rem',
              lineHeight: 1.6,
              color: T.text2,
              overflowX: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {JSON.stringify(section.body, null, 2)}
          </pre>
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

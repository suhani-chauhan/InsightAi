import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { T } from '../dashboard/tokens';
import { askInsightAI, queryDataset } from '../../services/dataScience';
import type { NlQueryResult } from '../../types/dataScience';

const SUGGESTIONS = [
  'What are the biggest data quality problems?',
  'What should I clean first?',
  'Show the top 10 rows by the largest numeric column',
  'What is the average of each numeric column, grouped by the first category?',
  'How many rows are there per category?',
  'Which model performed best and why?',
];

interface Turn {
  q: string;
  kind: 'narrative' | 'data';
  answer?: string;
  llmAvailable?: boolean;
  query?: NlQueryResult;
}

// Heuristic: does the question want rows/aggregates from the data itself?
const DATA_HINT = /\b(how many|count|sum|total|average|avg|mean|median|max|min|top \d|bottom \d|group(ed)? by|per |by |list|show|rows where|filter|distinct|between|greater than|less than|highest|lowest|most|least|breakdown)\b/i;

export function AskPanel({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  const ask = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setQuestion('');
    try {
      if (DATA_HINT.test(trimmed)) {
        const res = await queryDataset(sessionId, trimmed);
        if (res.answered) {
          setTurns((prev) => [...prev, { q: trimmed, kind: 'data', query: res }]);
          return;
        }
        // Not answerable as a data query — fall through to narrative.
      }
      const res = await askInsightAI(sessionId, trimmed);
      setTurns((prev) => [...prev, { q: trimmed, kind: 'narrative', answer: res.answer, llmAvailable: res.llm_available }]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { q: trimmed, kind: 'narrative', answer: err instanceof Error ? err.message : 'Something went wrong.', llmAvailable: false },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside
      style={{
        width: 400,
        flexShrink: 0,
        borderLeft: '1px solid rgba(0,0,0,0.1)',
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      <header style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900 }}>
          <Sparkles size={16} /> Ask InsightAI
        </span>
        <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: T.text3 }}>
          <X size={16} />
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {turns.length === 0 && (
          <div style={{ display: 'grid', gap: 8 }}>
            <p style={{ fontSize: '0.78rem', color: T.text3, lineHeight: 1.6, margin: 0 }}>
              Ask about the analysis (quality, EDA, models) <strong>or query the data itself</strong> in plain English — InsightAI writes read-only SQL and runs it on your dataset.
            </p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => ask(s)}
                style={{
                  textAlign: 'left',
                  padding: '10px 12px',
                  border: '1px solid rgba(0,0,0,0.1)',
                  background: T.bg,
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                  color: T.text2,
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {turns.map((turn, i) => (
          <div key={i} style={{ marginBottom: 18 }}>
            <div style={{ fontWeight: 700, fontSize: '0.82rem', marginBottom: 6 }}>{turn.q}</div>
            {turn.kind === 'narrative' ? (
              <>
                <div style={{ fontSize: '0.82rem', color: T.text2, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{turn.answer}</div>
                {turn.llmAvailable === false && (
                  <div style={{ marginTop: 4, fontFamily: T.fontMono, fontSize: '0.6rem', color: T.text3 }}>
                    narrative layer offline — computed analysis still accurate
                  </div>
                )}
              </>
            ) : (
              <QueryResult res={turn.query!} />
            )}
          </div>
        ))}
        {busy && <div style={{ fontFamily: T.fontMono, fontSize: '0.72rem', color: T.text3 }}>Working…</div>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        style={{ padding: 14, borderTop: '1px solid rgba(0,0,0,0.08)', display: 'flex', gap: 8 }}
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about — or query — this dataset…"
          style={{ flex: 1, padding: '10px 12px', border: `1.5px solid ${T.border2}`, fontSize: '0.82rem' }}
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          style={{
            padding: '10px 16px',
            border: `1.5px solid ${T.text}`,
            background: T.text,
            color: '#fff',
            fontFamily: T.fontMono,
            fontSize: '0.68rem',
            fontWeight: 800,
            textTransform: 'uppercase',
            cursor: 'pointer',
            opacity: busy || !question.trim() ? 0.5 : 1,
          }}
        >
          Ask
        </button>
      </form>
    </aside>
  );
}

function QueryResult({ res }: { res: NlQueryResult }) {
  if (!res.answered) {
    return <div style={{ fontSize: '0.8rem', color: T.text3 }}>{res.reason}</div>;
  }
  const cols = res.columns ?? [];
  const rows = res.rows ?? [];
  return (
    <div>
      <pre
        style={{
          margin: '0 0 8px',
          padding: '8px 10px',
          background: T.bg,
          border: '1px solid rgba(0,0,0,0.08)',
          fontFamily: T.fontMono,
          fontSize: '0.68rem',
          color: T.text2,
          whiteSpace: 'pre-wrap',
          overflowX: 'auto',
        }}
      >
        {res.sql}
      </pre>
      <div style={{ overflowX: 'auto', border: '1px solid rgba(0,0,0,0.08)' }}>
        <table style={{ borderCollapse: 'collapse', fontSize: '0.72rem', fontFamily: T.fontMono, minWidth: '100%' }}>
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c} style={{ padding: '5px 8px', textAlign: 'left', color: T.text3, borderBottom: '1px solid rgba(0,0,0,0.1)', whiteSpace: 'nowrap' }}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 50).map((r, i) => (
              <tr key={i} style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                {cols.map((c) => (
                  <td key={c} style={{ padding: '5px 8px', color: T.text2, whiteSpace: 'nowrap' }}>
                    {r[c] === null || r[c] === undefined ? '∅' : String(r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 4, fontFamily: T.fontMono, fontSize: '0.62rem', color: T.text3 }}>
        {res.row_count} row{res.row_count === 1 ? '' : 's'}
        {res.truncated ? ' (truncated)' : ''}
        {rows.length > 50 ? ' · showing first 50' : ''}
      </div>
    </div>
  );
}

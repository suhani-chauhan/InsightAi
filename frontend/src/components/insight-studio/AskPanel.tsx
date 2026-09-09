import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { T } from '../dashboard/tokens';
import { askInsightMind } from '../../services/dataScience';

const SUGGESTIONS = [
  'What are the biggest data quality problems?',
  'What should I clean first?',
  'Which variables are correlated?',
  'Should I use classification or regression?',
  'Which model performed best and why?',
  'What patterns do you see?',
];

interface Turn {
  q: string;
  a: string;
  llmAvailable: boolean;
}

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
      const res = await askInsightMind(sessionId, trimmed);
      setTurns((prev) => [...prev, { q: trimmed, a: res.answer, llmAvailable: res.llm_available }]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { q: trimmed, a: err instanceof Error ? err.message : 'Something went wrong.', llmAvailable: false },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside
      style={{
        width: 380,
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
          <Sparkles size={16} /> Ask InsightMind
        </span>
        <button type="button" onClick={onClose} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: T.text3 }}>
          <X size={16} />
        </button>
      </header>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {turns.length === 0 && (
          <div style={{ display: 'grid', gap: 8 }}>
            <p style={{ fontSize: '0.78rem', color: T.text3, lineHeight: 1.6, margin: 0 }}>
              Grounded in this session's computed analysis — profiling, quality, EDA statistics and model metrics.
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
          <div key={i} style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: '0.82rem', marginBottom: 6 }}>{turn.q}</div>
            <div style={{ fontSize: '0.82rem', color: T.text2, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{turn.a}</div>
            {!turn.llmAvailable && (
              <div style={{ marginTop: 4, fontFamily: T.fontMono, fontSize: '0.6rem', color: T.text3 }}>
                narrative layer offline — computed analysis still accurate
              </div>
            )}
          </div>
        ))}
        {busy && <div style={{ fontFamily: T.fontMono, fontSize: '0.72rem', color: T.text3 }}>Thinking…</div>}
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
          placeholder="Ask about this dataset…"
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

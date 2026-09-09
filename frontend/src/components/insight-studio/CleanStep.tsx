import { useEffect, useMemo, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, ErrorBlock, LoadingBlock, Panel, Pill, num, riskColor } from './ui';
import {
  cleaningApply,
  cleaningPreview,
  cleaningRecommendations,
  cleaningReset,
  cleaningUndo,
} from '../../services/dataScience';
import type {
  CleaningApplyResult,
  CleaningPreview,
  CleaningRecommendation,
  CleaningRecommendations,
  WorkspaceStep,
} from '../../types/dataScience';

export function CleanStep({
  sessionId,
  onChanged,
  onGoto,
}: {
  sessionId: string;
  onChanged: () => void;
  onGoto: (step: WorkspaceStep) => void;
}) {
  const [recs, setRecs] = useState<CleaningRecommendations | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<CleaningPreview | null>(null);
  const [applied, setApplied] = useState<CleaningApplyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    cleaningRecommendations(sessionId)
      .then((res) => {
        setRecs(res);
        setSelected(new Set(res.recommendations.filter((r) => r.risk === 'low').map((r) => r.id)));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load recommendations'))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(load, [sessionId]);

  const chosenOps = useMemo(
    () => (recs?.recommendations ?? []).filter((r) => selected.has(r.id)).map((r) => r.operation),
    [recs, selected],
  );

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const runPreview = async () => {
    if (!chosenOps.length) return;
    setBusy('preview');
    setError(null);
    try {
      setPreview(await cleaningPreview(sessionId, chosenOps));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setBusy(null);
    }
  };

  const runApply = async () => {
    if (!chosenOps.length) return;
    setBusy('apply');
    setError(null);
    try {
      const res = await cleaningApply(sessionId, chosenOps);
      setApplied(res);
      setPreview(null);
      onChanged();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Apply failed');
    } finally {
      setBusy(null);
    }
  };

  const runUndo = async () => {
    setBusy('undo');
    try {
      await cleaningUndo(sessionId);
      setApplied(null);
      onChanged();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Undo failed');
    } finally {
      setBusy(null);
    }
  };

  const runReset = async () => {
    setBusy('reset');
    try {
      await cleaningReset(sessionId);
      setApplied(null);
      setPreview(null);
      onChanged();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed');
    } finally {
      setBusy(null);
    }
  };

  const applySafe = () => {
    if (!recs) return;
    setSelected(new Set(recs.recommendations.filter((r) => r.risk === 'low').map((r) => r.id)));
    setTimeout(runApply, 0);
  };

  if (loading && !recs) return <LoadingBlock label="Building cleaning recommendations…" />;

  return (
    <div>
      {error && <ErrorBlock message={error} onRetry={() => setError(null)} />}

      {applied && (
        <Panel title="Cleaning applied" subtitle={applied.narrative ?? undefined}>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <BeforeAfter label="Rows" before={applied.step.rows_before} after={applied.step.rows_after} />
            <BeforeAfter label="Columns" before={applied.step.cols_before} after={applied.step.cols_after} />
            <BeforeAfter label="Quality" before={applied.quality_before.overall} after={applied.quality_after.overall} good />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Btn small variant="ghost" onClick={runUndo} disabled={busy === 'undo'}>
              Undo last step
            </Btn>
            <Btn small variant="danger" onClick={runReset} disabled={busy === 'reset'}>
              Reset to original
            </Btn>
            <Btn small onClick={() => onGoto('explore')}>
              Explore clean data
            </Btn>
          </div>
        </Panel>
      )}

      <Panel
        title="Recommended cleaning"
        subtitle={
          recs
            ? `${recs.safe_fix_count} safe fix(es), ${recs.review_count} to review. The AI recommends — it never cleans blindly.`
            : undefined
        }
        actions={
          <>
            <Btn small variant="ghost" onClick={applySafe} disabled={!recs?.safe_fix_count || !!busy}>
              Apply {recs?.safe_fix_count ?? 0} safe fixes
            </Btn>
            <Btn small variant="ghost" onClick={runPreview} disabled={!chosenOps.length || !!busy}>
              {busy === 'preview' ? 'Previewing…' : 'Preview'}
            </Btn>
            <Btn small onClick={runApply} disabled={!chosenOps.length || !!busy}>
              {busy === 'apply' ? 'Applying…' : `Apply ${chosenOps.length}`}
            </Btn>
          </>
        }
      >
        {!recs?.recommendations.length ? (
          <div style={{ padding: 24, textAlign: 'center', color: T.green, fontSize: '0.85rem' }}>
            No cleaning issues detected — the dataset looks ready.
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {recs.recommendations.map((rec) => (
              <RecRow key={rec.id} rec={rec} checked={selected.has(rec.id)} onToggle={() => toggle(rec.id)} />
            ))}
          </div>
        )}
      </Panel>

      {preview && (
        <Panel title="Preview" subtitle="Nothing is applied yet. This is a dry run on the analysis copy.">
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 16 }}>
            <BeforeAfter label="Rows" before={preview.before.rows} after={preview.after.rows} />
            <BeforeAfter label="Missing cells" before={preview.before.missing_cells} after={preview.after.missing_cells} good />
            <BeforeAfter label="Duplicate rows" before={preview.before.duplicate_rows} after={preview.after.duplicate_rows} good />
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: T.text3, fontFamily: T.fontMono, fontSize: '0.62rem', textTransform: 'uppercase' }}>
                  <th style={{ padding: '6px 10px' }}>Column</th>
                  <th style={{ padding: '6px 10px' }}>Status</th>
                  <th style={{ padding: '6px 10px' }}>Missing</th>
                  <th style={{ padding: '6px 10px' }}>Type</th>
                  <th style={{ padding: '6px 10px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {preview.column_diff
                  .filter((d) => d.status !== 'unchanged')
                  .map((d) => (
                    <tr key={d.column} style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                      <td style={{ padding: '6px 10px', fontWeight: 700 }}>{d.column}</td>
                      <td style={{ padding: '6px 10px' }}>
                        <Pill color={d.status === 'dropped' ? T.red : d.status === 'added' ? T.green : T.accent}>{d.status}</Pill>
                      </td>
                      <td style={{ padding: '6px 10px' }}>
                        {num(d.missing_before ?? 0)} → {num(d.missing_after ?? 0)}
                      </td>
                      <td style={{ padding: '6px 10px', fontFamily: T.fontMono, fontSize: '0.68rem' }}>
                        {d.dtype_before ?? '—'} → {d.dtype_after ?? '—'}
                      </td>
                      <td style={{ padding: '6px 10px', color: T.text2 }}>{d.action || '—'}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}

function RecRow({
  rec,
  checked,
  onToggle,
}: {
  rec: CleaningRecommendation;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label
      style={{
        display: 'flex',
        gap: 12,
        border: `1px solid ${checked ? T.text : 'rgba(0,0,0,0.08)'}`,
        padding: '14px 16px',
        background: checked ? T.bg : '#fff',
        cursor: 'pointer',
      }}
    >
      <input type="checkbox" checked={checked} onChange={onToggle} style={{ marginTop: 3 }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 4 }}>
          <Pill color={riskColor[rec.risk]}>{rec.risk} risk</Pill>
          <strong style={{ fontSize: '0.85rem' }}>{rec.solution}</strong>
        </div>
        <div style={{ fontSize: '0.79rem', color: T.text2, lineHeight: 1.6 }}>
          <div>
            <span style={{ color: T.text3 }}>Problem: </span>
            {rec.problem}
          </div>
          <div>
            <span style={{ color: T.text3 }}>Why: </span>
            {rec.reason}
          </div>
          <div>
            <span style={{ color: T.text3 }}>Impact: </span>
            {rec.expected_impact}
          </div>
        </div>
      </div>
    </label>
  );
}

function BeforeAfter({
  label,
  before,
  after,
  good,
}: {
  label: string;
  before: number;
  after: number;
  good?: boolean;
}) {
  const improved = good ? after < before || after > before : after !== before;
  const better = good ? (label === 'Quality' ? after > before : after < before) : true;
  return (
    <div>
      <div style={{ fontFamily: T.fontMono, fontSize: '0.62rem', textTransform: 'uppercase', color: T.text3, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900, fontSize: '1.2rem' }}>
        <span style={{ color: T.text3 }}>{num(before)}</span>
        <span style={{ color: T.text3, margin: '0 8px' }}>→</span>
        <span style={{ color: improved ? (better ? T.green : T.orange) : T.text }}>{num(after)}</span>
      </div>
    </div>
  );
}

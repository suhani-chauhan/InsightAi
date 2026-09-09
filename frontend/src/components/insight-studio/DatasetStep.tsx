import { useEffect, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn, EmptyHint, LoadingBlock, Panel, Pill, StatTile, TileGrid, num } from './ui';
import { profileSession } from '../../services/dataScience';
import type { DatasetOverview, WorkspaceStep } from '../../types/dataScience';

const KIND_COLOR: Record<string, string> = {
  numeric: T.accent,
  categorical: T.purple,
  datetime: T.green,
  boolean: T.yellow,
  text: T.orange,
  empty: T.red,
};

export function DatasetStep({
  sessionId,
  dataset,
  onGoto,
}: {
  sessionId: string;
  dataset: DatasetOverview;
  onGoto: (step: WorkspaceStep) => void;
}) {
  const [profile, setProfile] = useState<{ dataset: Record<string, unknown>; columns: Record<string, unknown>[] } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    profileSession(sessionId)
      .then((res) => alive && setProfile(res))
      .catch(() => undefined)
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [sessionId]);

  const kindCounts = dataset.columns.reduce<Record<string, number>>((acc, c) => {
    acc[c.kind] = (acc[c.kind] || 0) + 1;
    return acc;
  }, {});

  const d = profile?.dataset ?? {};

  return (
    <div>
      <Panel
        title={dataset.name}
        subtitle={
          dataset.source_detail?.is_demo
            ? 'Demo dataset — seeded with missing values, duplicates, inconsistent categories and outliers so every step has something to show.'
            : `Analysis copy from ${dataset.source.replace('_', ' ')}. The source is never modified.`
        }
        actions={
          <>
            <Btn small variant="ghost" onClick={() => onGoto('quality')}>
              Profile & Quality
            </Btn>
            <Btn small onClick={() => onGoto('clean')}>
              Clean Dataset
            </Btn>
          </>
        }
      >
        <TileGrid>
          <StatTile label="Rows" value={num(dataset.n_rows)} hint={dataset.sampled ? `sampled from ${num(dataset.original_row_count)}` : undefined} />
          <StatTile label="Columns" value={num(dataset.n_cols)} />
          <StatTile label="Missing cells" value={num(d.missing_cells ?? '—')} hint={d.missing_pct !== undefined ? `${d.missing_pct}%` : undefined} accent={Number(d.missing_pct) > 0 ? T.orange : T.green} />
          <StatTile label="Duplicate rows" value={num(d.duplicate_rows ?? '—')} accent={Number(d.duplicate_rows) > 0 ? T.orange : T.green} />
          <StatTile label="Cleaning steps" value={num(dataset.cleaning_steps ?? 0)} />
          <StatTile label="Model trained" value={dataset.has_model ? 'Yes' : 'No'} accent={dataset.has_model ? T.green : T.text3} />
        </TileGrid>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
          {Object.entries(kindCounts).map(([kind, count]) => (
            <Pill key={kind} color={KIND_COLOR[kind] || T.text3}>
              {count} {kind}
            </Pill>
          ))}
        </div>
      </Panel>

      <Panel title="Columns" subtitle="Type is inferred deterministically and drives profiling, cleaning and ML preprocessing.">
        {loading && !profile ? (
          <LoadingBlock label="Profiling dataset…" />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: T.text3, fontFamily: T.fontMono, fontSize: '0.64rem', textTransform: 'uppercase' }}>
                  <th style={th}>Column</th>
                  <th style={th}>Kind</th>
                  <th style={th}>Missing</th>
                  <th style={th}>Unique</th>
                  <th style={th}>Mean / Mode</th>
                  <th style={th}>Min</th>
                  <th style={th}>Max</th>
                </tr>
              </thead>
              <tbody>
                {(profile?.columns ?? dataset.columns.map((c) => ({ ...c }))).map((col) => {
                  const c = col as Record<string, unknown>;
                  return (
                    <tr key={String(c.name)} style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                      <td style={{ ...td, fontWeight: 700 }}>{String(c.name)}</td>
                      <td style={td}>
                        <Pill color={KIND_COLOR[String(c.kind)] || T.text3}>{String(c.kind)}</Pill>
                      </td>
                      <td style={td}>
                        {num(c.missing ?? 0)}
                        {c.missing_pct !== undefined && Number(c.missing_pct) > 0 ? (
                          <span style={{ color: T.orange }}> ({String(c.missing_pct)}%)</span>
                        ) : null}
                      </td>
                      <td style={td}>{num(c.unique ?? '—')}</td>
                      <td style={td}>{c.mean !== undefined && c.mean !== null ? num(c.mean) : c.mode !== undefined && c.mode !== null ? String(c.mode) : '—'}</td>
                      <td style={td}>{c.min !== undefined && c.min !== null ? String(c.min) : '—'}</td>
                      <td style={td}>{c.max !== undefined && c.max !== null ? String(c.max) : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Sample rows">
        {dataset.sample_rows.length === 0 ? (
          <EmptyHint>No rows to preview.</EmptyHint>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', fontSize: '0.75rem', fontFamily: T.fontMono }}>
              <thead>
                <tr>
                  {dataset.columns.map((c) => (
                    <th key={c.name} style={{ ...th, whiteSpace: 'nowrap' }}>
                      {c.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataset.sample_rows.map((row, i) => (
                  <tr key={i} style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                    {dataset.columns.map((c) => (
                      <td key={c.name} style={{ ...td, whiteSpace: 'nowrap' }}>
                        {row[c.name] === null || row[c.name] === undefined ? (
                          <span style={{ color: T.red }}>∅</span>
                        ) : (
                          String(row[c.name])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

const th: React.CSSProperties = { padding: '8px 12px' };
const td: React.CSSProperties = { padding: '8px 12px', color: T.text2 };

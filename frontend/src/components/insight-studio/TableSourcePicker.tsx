import { useEffect, useState } from 'react';
import { T } from '../dashboard/tokens';
import { Btn } from './ui';
import { getSchema, listConnections } from '../../services/api';
import type { DatabaseConnection, SchemaTable } from '../../types/api';

interface Props {
  onPick: (input: { connectionId: string; table: string; schema?: string }) => void;
  disabled?: boolean;
}

/** Connection -> table picker that reuses the existing connections/schema APIs. */
export function TableSourcePicker({ onPick, disabled }: Props) {
  const [connections, setConnections] = useState<DatabaseConnection[] | null>(null);
  const [connectionId, setConnectionId] = useState('');
  const [tables, setTables] = useState<SchemaTable[] | null>(null);
  const [tableName, setTableName] = useState('');
  const [loadingTables, setLoadingTables] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listConnections()
      .then((rows) => {
        setConnections(rows);
        if (rows.length === 1) setConnectionId(rows[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load connections'));
  }, []);

  useEffect(() => {
    if (!connectionId) {
      setTables(null);
      setTableName('');
      return;
    }
    setLoadingTables(true);
    setError(null);
    getSchema(connectionId)
      .then((res) => setTables(res.tables))
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load this connection’s schema'))
      .finally(() => setLoadingTables(false));
  }, [connectionId]);

  const submit = () => {
    if (!connectionId || !tableName) return;
    const dot = tableName.lastIndexOf('.');
    const schema = dot > 0 ? tableName.slice(0, dot) : undefined;
    const table = dot > 0 ? tableName.slice(dot + 1) : tableName;
    onPick({ connectionId, table, schema });
  };

  if (connections === null && !error) {
    return <div style={{ fontFamily: T.fontMono, fontSize: '0.72rem', color: T.text3 }}>Loading connections…</div>;
  }
  if (connections && connections.length === 0) {
    return (
      <div style={{ fontSize: '0.8rem', color: T.text3 }}>
        No database connections yet — add one under <a href="/connections">Connections</a>.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center' }}>
      <select value={connectionId} onChange={(e) => setConnectionId(e.target.value)} style={selectStyle} disabled={disabled}>
        <option value="">Connection…</option>
        {(connections ?? []).map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({c.database})
          </option>
        ))}
      </select>
      <select
        value={tableName}
        onChange={(e) => setTableName(e.target.value)}
        style={selectStyle}
        disabled={disabled || !connectionId || loadingTables}
      >
        <option value="">{loadingTables ? 'Loading tables…' : 'Table…'}</option>
        {(tables ?? []).map((t) => (
          <option key={t.name} value={t.name}>
            {t.name}
            {t.row_count != null ? ` · ${t.row_count.toLocaleString()} rows` : ''}
          </option>
        ))}
      </select>
      <Btn small onClick={submit} disabled={disabled || !connectionId || !tableName}>
        Analyze table
      </Btn>
      {error && <div style={{ width: '100%', color: T.red, fontSize: '0.75rem' }}>{error}</div>}
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: `1.5px solid ${T.border2}`,
  fontFamily: T.fontMono,
  fontSize: '0.72rem',
  background: '#fff',
};

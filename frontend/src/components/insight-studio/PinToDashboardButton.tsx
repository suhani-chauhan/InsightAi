import { useState } from 'react';
import { Check, LayoutDashboard } from 'lucide-react';
import { T } from '../dashboard/tokens';
import { Btn } from './ui';
import { addDashboardWidget } from '../../services/api';
import { useDashboardCatalog } from '../../hooks/useDashboardCatalog';
import { layoutDims } from '../../utils/dashboardUtils';
import type { WidgetSize } from '../../types/dashboard';

interface Props {
  title: string;
  vizType: 'kpi' | 'bar' | 'line' | 'area' | 'donut' | 'table';
  columns: string[];
  rows: Array<Record<string, unknown>>;
  size?: WidgetSize;
}

/** Pins a computed Data Science artifact to a dashboard as a static widget. */
export function PinToDashboardButton({ title, vizType, columns, rows, size = 'half' }: Props) {
  const [open, setOpen] = useState(false);
  const { dashboards, loading, createNewDashboard } = useDashboardCatalog({ autoLoad: open });
  const [dashId, setDashId] = useState<string>(() => localStorage.getItem('lastUsedDashboardId') || '');
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const pin = async (targetId: string) => {
    setStatus('saving');
    setError(null);
    try {
      const dims = layoutDims(size, vizType);
      await addDashboardWidget({
        dashboard_id: targetId,
        title,
        viz_type: vizType,
        size,
        columns,
        rows,
        cadence: 'Manual only',
        w: dims.w,
        h: dims.h,
        minW: dims.minW,
        minH: dims.minH,
        bar_orientation: 'horizontal',
      });
      localStorage.setItem('lastUsedDashboardId', targetId);
      setStatus('saved');
      setTimeout(() => {
        setOpen(false);
        setStatus('idle');
      }, 1100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pin');
      setStatus('error');
    }
  };

  const handleConfirm = async () => {
    let target = dashId;
    if (!target) {
      if (dashboards.length) {
        target = dashboards[0].id;
      } else {
        try {
          const created = await createNewDashboard({ name: 'InsightAI', icon: '🧪' });
          target = created.id;
        } catch {
          setError('Could not create a dashboard');
          setStatus('error');
          return;
        }
      }
    }
    void pin(target);
  };

  if (!open) {
    return (
      <Btn small variant="ghost" onClick={() => setOpen(true)}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <LayoutDashboard size={12} /> Pin to dashboard
        </span>
      </Btn>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {status === 'saved' ? (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: T.green, fontSize: '0.75rem', fontFamily: T.fontMono }}>
          <Check size={13} strokeWidth={3} /> Pinned
        </span>
      ) : (
        <>
          <select
            value={dashId}
            onChange={(e) => setDashId(e.target.value)}
            disabled={loading || status === 'saving'}
            style={{ padding: '6px 8px', border: `1.5px solid ${T.border2}`, fontFamily: T.fontMono, fontSize: '0.7rem', background: '#fff' }}
          >
            <option value="">{loading ? 'Loading…' : dashboards.length ? 'Choose dashboard…' : 'New "InsightAI" dashboard'}</option>
            {dashboards.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.widget_count})
              </option>
            ))}
          </select>
          <Btn small onClick={handleConfirm} disabled={status === 'saving'}>
            {status === 'saving' ? 'Pinning…' : 'Pin'}
          </Btn>
          <button
            type="button"
            onClick={() => setOpen(false)}
            style={{ border: 'none', background: 'transparent', color: T.text3, fontSize: '0.7rem', cursor: 'pointer', fontFamily: T.fontMono }}
          >
            cancel
          </button>
        </>
      )}
      {error && <span style={{ color: T.red, fontSize: '0.68rem' }}>{error}</span>}
    </div>
  );
}

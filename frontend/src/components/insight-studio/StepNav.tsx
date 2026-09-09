import { Check } from 'lucide-react';
import { T } from '../dashboard/tokens';
import type { WorkspaceStep } from '../../types/dataScience';

const STEPS: { key: WorkspaceStep; label: string }[] = [
  { key: 'dataset', label: 'Dataset' },
  { key: 'quality', label: 'Quality' },
  { key: 'clean', label: 'Clean' },
  { key: 'explore', label: 'Explore' },
  { key: 'ml', label: 'ML' },
  { key: 'report', label: 'Report' },
];

export function StepNav({
  active,
  completed,
  onSelect,
}: {
  active: WorkspaceStep;
  completed: Set<WorkspaceStep>;
  onSelect: (step: WorkspaceStep) => void;
}) {
  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        flexWrap: 'wrap',
        padding: '14px 0',
        borderBottom: '1px solid rgba(0,0,0,0.08)',
        marginBottom: 24,
      }}
    >
      {STEPS.map((step, i) => {
        const isActive = step.key === active;
        const isDone = completed.has(step.key);
        return (
          <div key={step.key} style={{ display: 'flex', alignItems: 'center' }}>
            <button
              type="button"
              onClick={() => onSelect(step.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 14px',
                border: `1.5px solid ${isActive ? T.text : 'rgba(0,0,0,0.12)'}`,
                background: isActive ? T.text : isDone ? T.greenDim : '#fff',
                color: isActive ? '#fff' : isDone ? T.green : T.text3,
                fontFamily: T.fontMono,
                fontSize: '0.7rem',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <span
                style={{
                  width: 18,
                  height: 18,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: `1.5px solid currentColor`,
                  fontSize: '0.62rem',
                }}
              >
                {isDone && !isActive ? <Check size={11} strokeWidth={3} /> : i + 1}
              </span>
              {step.label}
            </button>
            {i < STEPS.length - 1 && (
              <span style={{ width: 16, height: 1.5, background: 'rgba(0,0,0,0.15)' }} />
            )}
          </div>
        );
      })}
    </nav>
  );
}

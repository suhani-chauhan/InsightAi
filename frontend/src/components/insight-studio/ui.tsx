import React from 'react';
import { T } from '../dashboard/tokens';

export const severityColor: Record<string, string> = {
  high: T.red,
  medium: T.orange,
  low: T.yellow,
  info: T.text3,
};

export const gradeColor: Record<string, string> = {
  excellent: T.green,
  good: T.green,
  fair: T.yellow,
  poor: T.orange,
  critical: T.red,
};

export const riskColor: Record<string, string> = {
  low: T.green,
  medium: T.orange,
  high: T.red,
};

export function Panel({
  title,
  subtitle,
  actions,
  children,
  style,
}: {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <section
      style={{
        background: '#fff',
        border: '1px solid rgba(0,0,0,0.08)',
        padding: 24,
        marginBottom: 20,
        ...style,
      }}
    >
      {(title || actions) && (
        <header
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
            marginBottom: title ? 18 : 0,
          }}
        >
          <div>
            {title && (
              <h3
                style={{
                  fontFamily: T.fontHead,
                  fontStyle: 'italic',
                  fontWeight: 900,
                  fontSize: '1.25rem',
                  color: T.text,
                  margin: 0,
                }}
              >
                {title}
              </h3>
            )}
            {subtitle && (
              <p style={{ margin: '4px 0 0', color: T.text3, fontSize: '0.8rem', lineHeight: 1.6 }}>
                {subtitle}
              </p>
            )}
          </div>
          {actions && <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Btn({
  children,
  onClick,
  variant = 'primary',
  disabled,
  small,
  title,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'ghost' | 'danger';
  disabled?: boolean;
  small?: boolean;
  title?: string;
}) {
  const base: React.CSSProperties = {
    padding: small ? '7px 14px' : '10px 20px',
    border: `1.5px solid ${T.text}`,
    fontFamily: T.fontMono,
    fontSize: small ? '0.68rem' : '0.72rem',
    fontWeight: 800,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
    transition: 'all 0.15s',
  };
  const skin: React.CSSProperties =
    variant === 'primary'
      ? { background: T.text, color: '#fff' }
      : variant === 'danger'
        ? { background: '#fff', color: T.red, borderColor: T.red }
        : { background: '#fff', color: T.text };
  return (
    <button type="button" title={title} onClick={onClick} disabled={disabled} style={{ ...base, ...skin }}>
      {children}
    </button>
  );
}

export function StatTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  accent?: string;
}) {
  return (
    <div style={{ background: T.bg, border: '1px solid rgba(0,0,0,0.06)', padding: '16px 18px' }}>
      <div
        style={{
          fontFamily: T.fontMono,
          fontSize: '0.62rem',
          textTransform: 'uppercase',
          letterSpacing: '0.12em',
          color: T.text3,
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: T.fontHead,
          fontStyle: 'italic',
          fontWeight: 900,
          fontSize: '1.6rem',
          color: accent || T.text,
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      {hint && <div style={{ marginTop: 6, fontSize: '0.72rem', color: T.text3 }}>{hint}</div>}
    </div>
  );
}

export function TileGrid({ children, min = 160 }: { children: React.ReactNode; min?: number }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fill, minmax(${min}px, 1fr))`,
        gap: 12,
      }}
    >
      {children}
    </div>
  );
}

export function LoadingBlock({ label = 'Working…' }: { label?: string }) {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center', color: T.text3, fontFamily: T.fontMono, fontSize: '0.8rem' }}>
      {label}
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      style={{
        padding: '20px 24px',
        background: T.redDim,
        border: `1px solid ${T.red}`,
        color: T.red,
        fontSize: '0.82rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
      }}
    >
      <span>{message}</span>
      {onRetry && <Btn variant="danger" small onClick={onRetry}>Retry</Btn>}
    </div>
  );
}

export function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: '40px 24px',
        textAlign: 'center',
        color: T.text3,
        fontSize: '0.85rem',
        lineHeight: 1.7,
        border: '1px dashed rgba(0,0,0,0.12)',
        background: T.bg,
      }}
    >
      {children}
    </div>
  );
}

export function Pill({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '3px 9px',
        background: `${color}18`,
        color,
        fontFamily: T.fontMono,
        fontSize: '0.62rem',
        fontWeight: 800,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        border: `1px solid ${color}55`,
      }}
    >
      {children}
    </span>
  );
}

export function num(value: unknown, digits = 2): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n)) return String(value);
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function pct(value: unknown): string {
  if (value === null || value === undefined) return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n)) return '—';
  return `${n.toFixed(1)}%`;
}

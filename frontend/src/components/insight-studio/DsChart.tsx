import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import { T } from '../dashboard/tokens';
import type { EdaChart } from '../../types/dataScience';

const PALETTE = [T.accent, T.purple, T.green, T.yellow, T.orange, T.red, '#14b8a6', '#8b5cf6'];

const axisStyle = { fontSize: 10, fontFamily: T.fontMono, fill: T.text3 };

export function DsChart({ chart, height = 240 }: { chart: EdaChart; height?: number }) {
  const data = (chart.data ?? []) as Record<string, unknown>[];

  if (chart.kind === 'histogram') {
    return (
      <Frame title={chart.title} height={height}>
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(0,0,0,0.06)" vertical={false} />
          <XAxis dataKey="bin" tick={axisStyle} interval="preserveStartEnd" />
          <YAxis tick={axisStyle} width={36} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill={T.accent} />
        </BarChart>
      </Frame>
    );
  }

  if (chart.kind === 'bar') {
    return (
      <Frame title={chart.title} height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(0,0,0,0.06)" horizontal={false} />
          <XAxis type="number" tick={axisStyle} />
          <YAxis type="category" dataKey="label" tick={axisStyle} width={110} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill={T.purple} />
        </BarChart>
      </Frame>
    );
  }

  if (chart.kind === 'pie') {
    return (
      <Frame title={chart.title} height={height}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="label" outerRadius={height / 2.8} innerRadius={height / 6}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Legend wrapperStyle={{ fontSize: 10, fontFamily: T.fontMono }} />
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </Frame>
    );
  }

  if (chart.kind === 'line') {
    return (
      <Frame title={chart.title} height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(0,0,0,0.06)" vertical={false} />
          <XAxis dataKey="x" tick={axisStyle} />
          <YAxis dataKey="y" tick={axisStyle} width={44} />
          <Tooltip contentStyle={tooltipStyle} />
          <Line type="monotone" dataKey="y" stroke={T.green} strokeWidth={2} dot={false} />
        </LineChart>
      </Frame>
    );
  }

  if (chart.kind === 'scatter') {
    return (
      <Frame title={chart.title} height={height}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="rgba(0,0,0,0.06)" />
          <XAxis type="number" dataKey="x" name={chart.x} tick={axisStyle} />
          <YAxis type="number" dataKey="y" name={chart.y} tick={axisStyle} width={44} />
          <ZAxis range={[24, 24]} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={data} fill={T.accent} fillOpacity={0.5} />
        </ScatterChart>
      </Frame>
    );
  }

  if (chart.kind === 'box') {
    const b = chart.data as {
      min: number; q1: number; median: number; q3: number; max: number;
      whisker_low: number; whisker_high: number; outlier_count: number;
    };
    return (
      <div style={frameStyle}>
        <ChartTitle>{chart.title}</ChartTitle>
        <BoxPlot b={b} />
      </div>
    );
  }

  if (chart.kind === 'correlation_heatmap') {
    const c = chart.data as { columns: string[]; matrix: (number | null)[][] };
    return (
      <div style={frameStyle}>
        <ChartTitle>{chart.title}</ChartTitle>
        <Heatmap columns={c.columns} matrix={c.matrix} />
      </div>
    );
  }

  return null;
}

const tooltipStyle = {
  fontSize: 11,
  fontFamily: T.fontMono,
  border: '1px solid rgba(0,0,0,0.12)',
  borderRadius: 0,
};

const frameStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid rgba(0,0,0,0.08)',
  padding: 14,
};

function ChartTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: T.fontMono,
        fontSize: '0.66rem',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: T.text3,
        marginBottom: 10,
      }}
    >
      {children}
    </div>
  );
}

function Frame({ title, height, children }: { title: string; height: number; children: React.ReactElement }) {
  return (
    <div style={frameStyle}>
      <ChartTitle>{title}</ChartTitle>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

function BoxPlot({
  b,
}: {
  b: { min: number; q1: number; median: number; q3: number; max: number; whisker_low: number; whisker_high: number; outlier_count: number };
}) {
  const lo = b.min;
  const hi = b.max;
  const span = hi - lo || 1;
  const x = (v: number) => `${((v - lo) / span) * 100}%`;
  return (
    <div>
      <div style={{ position: 'relative', height: 44, margin: '12px 0' }}>
        <div style={{ position: 'absolute', top: 21, left: x(b.whisker_low), right: `${100 - Number(x(b.whisker_high).replace('%', ''))}%`, height: 2, background: T.text3 }} />
        <div
          style={{
            position: 'absolute',
            top: 8,
            left: x(b.q1),
            width: x(b.q3 - b.q1 + lo),
            height: 28,
            background: T.accentDim,
            border: `1.5px solid ${T.accent}`,
          }}
        />
        <div style={{ position: 'absolute', top: 8, left: x(b.median), width: 2, height: 28, background: T.text }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: T.fontMono, fontSize: '0.62rem', color: T.text3 }}>
        <span>min {fmt(b.min)}</span>
        <span>Q1 {fmt(b.q1)}</span>
        <span>med {fmt(b.median)}</span>
        <span>Q3 {fmt(b.q3)}</span>
        <span>max {fmt(b.max)}</span>
      </div>
      <div style={{ marginTop: 6, fontSize: '0.72rem', color: b.outlier_count ? T.orange : T.text3 }}>
        {b.outlier_count} outlier{b.outlier_count === 1 ? '' : 's'} beyond 1.5×IQR
      </div>
    </div>
  );
}

function Heatmap({ columns, matrix }: { columns: string[]; matrix: (number | null)[][] }) {
  const color = (v: number | null) => {
    if (v === null) return 'transparent';
    const a = Math.abs(v);
    return v >= 0 ? `rgba(14,165,233,${a})` : `rgba(239,68,68,${a})`;
  };
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', fontFamily: T.fontMono, fontSize: '0.62rem' }}>
        <thead>
          <tr>
            <th />
            {columns.map((c) => (
              <th key={c} style={{ padding: 4, color: T.text3, writingMode: 'vertical-rl', maxHeight: 90 }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td style={{ padding: '4px 8px', color: T.text3, whiteSpace: 'nowrap' }}>{columns[i]}</td>
              {row.map((v, j) => (
                <td
                  key={j}
                  title={v === null ? '' : `${columns[i]} ↔ ${columns[j]}: ${v.toFixed(2)}`}
                  style={{
                    width: 34,
                    height: 26,
                    textAlign: 'center',
                    background: color(v),
                    border: '1px solid rgba(0,0,0,0.05)',
                    color: v !== null && Math.abs(v) > 0.5 ? '#fff' : T.text3,
                  }}
                >
                  {v === null ? '' : v.toFixed(1)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function fmt(v: number): string {
  return Math.abs(v) >= 1000 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toFixed(2);
}

import { useEffect, useMemo, useRef, useState } from 'react';
import { FlaskConical, Sparkles, Upload } from 'lucide-react';
import { MainShell } from '../components/common/MainShell';
import { T } from '../components/dashboard/tokens';
import { StepNav } from '../components/insight-studio/StepNav';
import { DatasetStep } from '../components/insight-studio/DatasetStep';
import { QualityStep } from '../components/insight-studio/QualityStep';
import { CleanStep } from '../components/insight-studio/CleanStep';
import { ExploreStep } from '../components/insight-studio/ExploreStep';
import { MlStep } from '../components/insight-studio/MlStep';
import { ReportStep } from '../components/insight-studio/ReportStep';
import { AskPanel } from '../components/insight-studio/AskPanel';
import { Btn, ErrorBlock } from '../components/insight-studio/ui';
import { useInsightStudioStore } from '../store/insightStudioStore';
import type { WorkspaceStep } from '../types/dataScience';

export function InsightStudioPage() {
  const {
    pending,
    sessionId,
    dataset,
    loading,
    error,
    createFromPending,
    startDemo,
    uploadFile,
    refreshOverview,
    reset,
  } = useInsightStudioStore();

  const [step, setStep] = useState<WorkspaceStep>('dataset');
  const [completed, setCompleted] = useState<Set<WorkspaceStep>>(new Set());
  const [target, setTarget] = useState<string | null>(null);
  const [askOpen, setAskOpen] = useState(false);

  useEffect(() => {
    if (pending && !sessionId) void createFromPending();
  }, [pending, sessionId, createFromPending]);

  useEffect(() => {
    const detected = dataset?.source_detail?.target;
    if (typeof detected === 'string' && !target) setTarget(detected);
  }, [dataset, target]);

  const markDone = (s: WorkspaceStep) => setCompleted((prev) => new Set(prev).add(s));

  const goto = (s: WorkspaceStep) => {
    markDone(step);
    setStep(s);
  };

  const body = useMemo(() => {
    if (!sessionId || !dataset) return null;
    switch (step) {
      case 'dataset':
        return <DatasetStep sessionId={sessionId} dataset={dataset} onGoto={goto} />;
      case 'quality':
        return <QualityStep sessionId={sessionId} onReport={() => markDone('quality')} onGoto={goto} />;
      case 'clean':
        return (
          <CleanStep
            sessionId={sessionId}
            onChanged={() => {
              markDone('clean');
              void refreshOverview();
            }}
            onGoto={goto}
          />
        );
      case 'explore':
        return (
          <ExploreStep
            sessionId={sessionId}
            dataset={dataset}
            target={target}
            onTargetChange={setTarget}
            onResult={() => markDone('explore')}
            onGoto={goto}
          />
        );
      case 'ml':
        return (
          <MlStep
            sessionId={sessionId}
            dataset={dataset}
            target={target}
            onTargetChange={setTarget}
            onResult={() => {
              markDone('ml');
              void refreshOverview();
            }}
            onGoto={goto}
          />
        );
      case 'report':
        return <ReportStep sessionId={sessionId} />;
      default:
        return null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, sessionId, dataset, target]);

  return (
    <MainShell
      title="Insight Studio"
      subtitle="Profile · Quality · Clean · Explore · ML · Report"
      badge={{ text: 'DATA SCIENCE', color: T.purple, icon: <FlaskConical size={12} /> }}
      headerActions={
        sessionId ? (
          <Btn small variant="ghost" onClick={() => setAskOpen((v) => !v)}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Sparkles size={12} /> Ask InsightMind
            </span>
          </Btn>
        ) : undefined
      }
    >
      <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 32px 48px' }}>
          {error && (
            <div style={{ marginTop: 20 }}>
              <ErrorBlock message={error} />
            </div>
          )}

          {!sessionId ? (
            <Landing loading={loading} onDemo={startDemo} onUpload={uploadFile} />
          ) : !dataset ? (
            <div style={{ padding: 60, textAlign: 'center', color: T.text3, fontFamily: T.fontMono }}>
              Loading analysis session…
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 20 }}>
                <div style={{ fontFamily: T.fontMono, fontSize: '0.7rem', color: T.text3, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  {dataset.name} · {dataset.n_rows.toLocaleString()} rows × {dataset.n_cols} cols
                </div>
                <button
                  type="button"
                  onClick={reset}
                  style={{ border: 'none', background: 'transparent', color: T.text3, fontFamily: T.fontMono, fontSize: '0.66rem', cursor: 'pointer', textTransform: 'uppercase' }}
                >
                  New analysis
                </button>
              </div>
              <StepNav active={step} completed={completed} onSelect={setStep} />
              {body}
            </>
          )}
        </div>
        {askOpen && sessionId && <AskPanel sessionId={sessionId} onClose={() => setAskOpen(false)} />}
      </div>
    </MainShell>
  );
}

function Landing({
  loading,
  onDemo,
  onUpload,
}: {
  loading: boolean;
  onDemo: () => void;
  onUpload: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div style={{ maxWidth: 620, margin: '80px auto 0', textAlign: 'center' }}>
      <div
        style={{
          width: 72,
          height: 72,
          margin: '0 auto 24px',
          background: 'rgba(0,0,0,0.03)',
          border: '1px solid rgba(0,0,0,0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: T.purple,
        }}
      >
        <FlaskConical size={32} strokeWidth={1.5} />
      </div>
      <h2 style={{ fontFamily: T.fontHead, fontStyle: 'italic', fontWeight: 900, fontSize: '2rem', color: T.text, marginBottom: 12 }}>
        Bring a dataset to the Studio
      </h2>
      <p style={{ color: T.text3, lineHeight: 1.8, fontSize: '0.88rem', marginBottom: 28 }}>
        Run a query in Chat, then choose <strong>Analyze Dataset</strong> on the result to profile it, fix data-quality
        issues, explore it, and train real models — without leaving InsightMind. Or upload a CSV, or start with the demo
        dataset.
      </p>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.tsv,text/csv,text/tab-separated-values"
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
            e.target.value = '';
          }}
        />
        <Btn onClick={() => fileRef.current?.click()} disabled={loading}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Upload size={12} /> Upload a CSV
          </span>
        </Btn>
        <Btn variant="ghost" onClick={onDemo} disabled={loading}>
          {loading ? 'Loading…' : 'Use the demo dataset'}
        </Btn>
      </div>
      <p style={{ color: T.text3, fontSize: '0.72rem', marginTop: 14, fontFamily: T.fontMono }}>
        CSV or TSV up to 12 MB · {'≤'} 100k rows · nothing is stored server-side
      </p>
    </div>
  );
}

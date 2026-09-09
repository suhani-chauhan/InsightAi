import { useLocation, useNavigate } from 'react-router-dom';
import { T } from '../dashboard/tokens';

export function LibrarySidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <aside
      style={{
        width: 220,
        flexShrink: 0,
        background: T.s1,
        borderRight: `1px solid ${T.border}`,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        fontFamily: T.fontBody,
      }}
    >
      <div style={{ padding: '16px 14px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontFamily: T.fontHead, fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.5px', padding: '4px 6px', marginBottom: 16 }}>
          <div style={{ width: 26, height: 26, borderRadius: 7, background: `linear-gradient(135deg, ${T.accent}, ${T.purple})`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', color: '#000', fontWeight: 800 }}>IA</div>
          <span style={{ color: T.text }}>Insight<span style={{ color: T.accent }}>AI</span></span>
        </div>

        <div style={{ fontSize: '0.62rem', fontWeight: 600, letterSpacing: '1.5px', color: T.text3, textTransform: 'uppercase', padding: '8px 8px 4px', fontFamily: T.fontMono }}>Main</div>

        <NavItem active={location.pathname === '/chat'} onClick={() => navigate('/chat')} icon="C" label="Chat" />
        <NavItem active={location.pathname === '/dashboard'} onClick={() => navigate('/dashboard')} icon="D" label="Dashboards" badge="3" />
        <NavItem active={location.pathname === '/library'} onClick={() => navigate('/library')} icon="L" label="Query Library" badge="24" />
        <NavItem active={location.pathname === '/analytics'} onClick={() => navigate('/analytics')} icon="A" label="Analytics" />

        <div style={{ fontSize: '0.62rem', fontWeight: 600, letterSpacing: '1.5px', color: T.text3, textTransform: 'uppercase', padding: '8px 8px 4px', fontFamily: T.fontMono, marginTop: 8 }}>Workspace</div>
        <NavItem active={location.pathname === '/connections'} onClick={() => navigate('/connections')} icon="N" label="Connections" badge="3" />
        <NavItem icon="!" label="Alerts" badge="2" badgeRed />
        <NavItem icon="G" label="Settings" />
      </div>

      <div style={{ marginTop: 'auto', padding: '12px 14px', borderTop: `1px solid ${T.border}` }}>
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '6px 4px', cursor: 'pointer', borderRadius: 8, transition: 'background 0.15s' }}
          onMouseEnter={(e) => (e.currentTarget.style.background = T.s2)}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          <div style={{ width: 28, height: 28, borderRadius: 8, flexShrink: 0, background: `linear-gradient(135deg, ${T.purple}, ${T.accent})`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.68rem', fontWeight: 700, color: '#fff' }}>AK</div>
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: T.text }}>Ahmad Khan</div>
            <div style={{ fontSize: '0.62rem', color: T.accent, fontFamily: T.fontMono }}>PRO PLAN</div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ active, icon, label, badge, badgeRed, onClick }: { active?: boolean; icon: string; label: string; badge?: string; badgeRed?: boolean; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 9,
        padding: '8px 10px',
        borderRadius: 8,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s',
        marginBottom: 1,
        color: active ? T.text : T.text3,
        fontSize: '0.82rem',
        border: `1px solid ${active ? 'rgba(0,229,255,0.12)' : 'transparent'}`,
        background: active ? T.s2 : 'transparent',
      }}
      onMouseEnter={(e) => {
        if (!active && onClick) {
          e.currentTarget.style.background = T.s2;
          e.currentTarget.style.color = T.text2;
        }
      }}
      onMouseLeave={(e) => {
        if (!active && onClick) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = T.text3;
        }
      }}
    >
      <div style={{ width: 15, height: 15, flexShrink: 0, color: active ? T.accent : 'inherit', borderRadius: 4, border: `1px solid ${active ? 'rgba(0,229,255,0.2)' : T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.6rem', fontFamily: T.fontMono, fontWeight: 700 }}>{icon}</div>
      {label}
      {badge && (
        <span
          style={{
            marginLeft: 'auto',
            background: badgeRed ? T.redDim : T.accentDim,
            color: badgeRed ? T.red : T.accent,
            fontSize: '0.62rem',
            fontFamily: T.fontMono,
            padding: '1px 6px',
            borderRadius: 10,
            border: `1px solid ${badgeRed ? 'rgba(248,113,113,0.2)' : 'rgba(0,229,255,0.2)'}`,
          }}
        >
          {badge}
        </span>
      )}
    </div>
  );
}

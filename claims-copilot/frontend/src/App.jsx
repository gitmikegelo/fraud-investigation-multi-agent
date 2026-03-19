import { useState } from 'react'
import CaseQueue from './components/CaseQueue'
import ChatPanel from './components/ChatPanel'
import RiskDashboard from './components/RiskDashboard'
import DossierPanel from './components/DossierPanel'

// ── SVG Icons ──────────────────────────────────────────────────────────────
const IconQueue = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
    <rect x="1.5" y="1.5" width="12" height="3" rx="1"/>
    <rect x="1.5" y="6" width="12" height="3" rx="1"/>
    <rect x="1.5" y="10.5" width="12" height="3" rx="1"/>
  </svg>
)
const IconChat = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.5 1.5h10a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5H5l-3 3V3A1.5 1.5 0 013.5 1.5z"/>
    <line x1="5" y1="5.5" x2="10" y2="5.5"/><line x1="5" y1="8" x2="8" y2="8"/>
  </svg>
)
const IconDashboard = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1,8 3.5,4.5 6,8 9,3 11.5,7 14,5"/>
  </svg>
)
const IconFile = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2a1.5 1.5 0 011.5-1.5H10L13 4v8.5A1.5 1.5 0 0111.5 14h-7A1.5 1.5 0 013 12.5V2z"/>
    <path d="M9.5.5V4H13"/><line x1="5" y1="7.5" x2="10" y2="7.5"/><line x1="5" y1="10" x2="8" y2="10"/>
  </svg>
)

const NAV = [
  { id: 'queue',     label: 'Claims Queue',  Icon: IconQueue },
  { id: 'copilot',   label: 'Copilot',       Icon: IconChat },
  { id: 'dashboard', label: 'Dashboard',     Icon: IconDashboard },
  { id: 'dossier',   label: 'Dossier',       Icon: IconFile },
]

export default function App() {
  const [activeView, setActiveView] = useState('queue')
  const [selectedCase, setSelectedCase] = useState(null)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--c-bg)' }}>

      {/* ── Sidebar ───────────────────────────────────────────────────── */}
      <aside style={{
        width: 218, flexShrink: 0,
        background: 'var(--c-sidebar)',
        display: 'flex', flexDirection: 'column',
        borderRight: '1px solid var(--c-sidebar-border)',
      }}>
        {/* Brand */}
        <div style={{ padding: '18px 18px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 9,
              background: 'rgba(99,102,241,0.18)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 10L5.5 5L8.5 8.5L11.5 3L14 6" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="2.5" cy="13" r="1.5" fill="#4f46e5"/>
                <circle cx="13.5" cy="13" r="1.5" fill="#818cf8"/>
              </svg>
            </div>
            <div>
              <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em', lineHeight: 1.2 }}>Claims Co-Pilot</div>
              <div style={{ color: '#475569', fontSize: 10, marginTop: 1 }}>Prudential</div>
            </div>
          </div>
          <div style={{ height: 1, background: 'var(--c-sidebar-border)' }} />
        </div>

        {/* Nav */}
        <nav style={{ padding: '12px 10px', flex: 1 }}>
          <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#334155', padding: '0 8px', marginBottom: 6 }}>
            Views
          </div>
          {NAV.map(({ id, label, Icon }) => {
            const active = activeView === id
            return (
              <button
                key={id}
                onClick={() => setActiveView(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 9,
                  width: '100%', padding: '7px 10px', borderRadius: 7,
                  border: 'none', cursor: 'pointer', marginBottom: 2,
                  background: active ? 'var(--c-sidebar-active)' : 'transparent',
                  color: active ? '#c7d2fe' : 'var(--c-sidebar-text)',
                  fontSize: 13, fontWeight: active ? 500 : 400,
                  transition: 'background 0.12s, color 0.12s', textAlign: 'left',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--c-sidebar-hover)' }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
              >
                <span style={{ opacity: active ? 1 : 0.55, flexShrink: 0 }}><Icon /></span>
                {label}
              </button>
            )
          })}
        </nav>

        {/* Selected case info */}
        {selectedCase && (
          <div style={{ padding: '0 14px 16px' }}>
            <div style={{ height: 1, background: 'var(--c-sidebar-border)', marginBottom: 14 }} />
            <div style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--c-sidebar-border)',
              borderRadius: 9, padding: '10px 12px',
            }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: '#64748b', marginBottom: 6 }}>
                Active Claim
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#818cf8', fontFamily: 'ui-monospace, monospace', marginBottom: 4 }}>
                {selectedCase.case_id}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 2 }}>
                {selectedCase.subject_name}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 4 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                  background: selectedCase.priority === 'HIGH' ? '#ef4444' : selectedCase.priority === 'MEDIUM' ? '#f59e0b' : '#6b7280',
                }} />
                <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>
                  {selectedCase.priority} ({selectedCase.risk_score})
                </span>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>

        {/* Top bar */}
        <div style={{
          height: 50, flexShrink: 0, background: 'var(--c-surface)',
          borderBottom: '1px solid var(--c-border)',
          display: 'flex', alignItems: 'center', padding: '0 20px', gap: 12,
        }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-text)', flex: 1 }}>
            {NAV.find(n => n.id === activeView)?.label || 'Examiner Workflow'}
          </span>
        </div>

        {/* View content */}
        <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
          {activeView === 'queue' && (
            <CaseQueue onSelectCase={(c) => { setSelectedCase(c); setActiveView('copilot') }} />
          )}
          {activeView === 'copilot' && selectedCase && (
            <ChatPanel
              caseId={selectedCase.case_id}
              caseType={selectedCase.case_type}
              caseSummary={selectedCase}
              onBack={() => setActiveView('queue')}
              onNavigateToDossier={() => setActiveView('dossier')}
            />
          )}
          {activeView === 'copilot' && !selectedCase && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--c-text-dim)', fontSize: 13 }}>
              Select a claim from the queue to start reviewing.
            </div>
          )}
          {activeView === 'dashboard' && (
            <RiskDashboard onSelectClaim={(c) => { setSelectedCase(c); setActiveView('copilot') }} />
          )}
          {activeView === 'dossier' && (
            <div style={{ height: '100%', overflow: 'auto', padding: 24 }}>
              <div style={{ maxWidth: 860, margin: '0 auto' }}>
                <DossierPanel caseId={selectedCase?.case_id} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

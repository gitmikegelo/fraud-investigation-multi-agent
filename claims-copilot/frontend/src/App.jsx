import { useState } from 'react'
import GraphView from './components/GraphView'
import EventTimeline from './components/EventTimeline'
import DossierPanel from './components/DossierPanel'
import NetworkGraph from './components/NetworkGraph'
import { useInvestigation } from './hooks/useInvestigation'

// ── SVG Icons ──────────────────────────────────────────────────────────────
const IconGrid = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="currentColor">
    <rect x="1" y="1" width="5.5" height="5.5" rx="1.2"/>
    <rect x="8.5" y="1" width="5.5" height="5.5" rx="1.2"/>
    <rect x="1" y="8.5" width="5.5" height="5.5" rx="1.2"/>
    <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1.2"/>
  </svg>
)
const IconFile = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2a1.5 1.5 0 011.5-1.5H10L13 4v8.5A1.5 1.5 0 0111.5 14h-7A1.5 1.5 0 013 12.5V2z"/>
    <path d="M9.5.5V4H13"/><line x1="5" y1="7.5" x2="10" y2="7.5"/><line x1="5" y1="10" x2="8" y2="10"/>
  </svg>
)
const IconHub = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round">
    <circle cx="7.5" cy="7.5" r="1.8"/>
    <circle cx="2" cy="3.5" r="1.5"/><circle cx="13" cy="3.5" r="1.5"/>
    <circle cx="2" cy="11.5" r="1.5"/><circle cx="13" cy="11.5" r="1.5"/>
    <line x1="7.5" y1="5.7" x2="2" y2="3.5"/><line x1="7.5" y1="5.7" x2="13" y2="3.5"/>
    <line x1="7.5" y1="9.3" x2="2" y2="11.5"/><line x1="7.5" y1="9.3" x2="13" y2="11.5"/>
  </svg>
)
const IconActivity = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1,8 3.5,4.5 6,8 9,3 11.5,7 14,5"/>
  </svg>
)

const NAV = [
  { id: 'overview',  label: 'Overview',      Icon: IconGrid },
  { id: 'dossier',   label: 'Dossier',        Icon: IconFile },
  { id: 'network',   label: 'Fraud Network',  Icon: IconHub },
  { id: 'activity',  label: 'Activity',       Icon: IconActivity },
]

const PHASE_COLOR = {
  'Initializing':        '#6366f1',
  'Initial Analysis':    '#a855f7',
  'Agent Orchestration': '#3b82f6',
  'Investigating':       '#16a34a',
  'Compiling':           '#d97706',
  'Done':                '#16a34a',
  '—':                   '#94a3b8',
}

export default function App() {
  const {
    status, activeNode, phase, loopCount, events, logs,
    dossier, findings, result, startInvestigation, nodeHistory, elapsed, initialClaims,
  } = useInvestigation()

  const [activeView, setActiveView] = useState('overview')
  const isRunning = status === 'running' || status === 'connecting'
  const isComplete = status === 'complete'
  const phaseColor = PHASE_COLOR[phase] || '#6366f1'

  const fmt = (s) => { const m = Math.floor(s / 60); return m > 0 ? `${m}m ${s % 60}s` : `${s}s` }

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
              <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em', lineHeight: 1.2 }}>ARIA</div>
              <div style={{ color: '#475569', fontSize: 10, marginTop: 1 }}>Fraud Intelligence</div>
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
                {id === 'dossier' && isComplete && (
                  <span style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
                )}
              </button>
            )
          })}
        </nav>

        {/* Status + Action */}
        <div style={{ padding: '0 14px 16px' }}>
          <div style={{ height: 1, background: 'var(--c-sidebar-border)', marginBottom: 14 }} />

          {/* Live status card */}
          {(isRunning || isComplete) && (
            <div style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--c-sidebar-border)',
              borderRadius: 9, padding: '10px 12px', marginBottom: 12,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 7 }}>
                <span style={{
                  width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                  background: isRunning ? '#22c55e' : '#475569',
                  boxShadow: isRunning ? '0 0 0 2.5px rgba(34,197,94,0.25)' : 'none',
                }} className={isRunning ? 'animate-pulse' : ''} />
                <span style={{
                  fontSize: 10, fontWeight: 700,
                  textTransform: 'uppercase', letterSpacing: '0.07em',
                  color: isRunning ? '#4ade80' : '#64748b',
                }}>
                  {isRunning ? 'Live' : 'Complete'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: phaseColor, fontWeight: 500, marginBottom: 4 }}>{phase}</div>
              {loopCount > 0 && (
                <div style={{ fontSize: 11, color: '#475569' }}>
                  Loop <span style={{ color: '#64748b', fontWeight: 600 }}>{loopCount}</span>
                </div>
              )}
              {elapsed > 0 && (
                <div style={{ fontSize: 11, color: '#475569', fontFamily: 'ui-monospace, monospace', marginTop: 2 }}>
                  ⏱ {fmt(elapsed)}
                </div>
              )}
            </div>
          )}

          <button
            onClick={startInvestigation}
            disabled={isRunning}
            style={{
              width: '100%', padding: '9px 0', borderRadius: 8, border: 'none',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              background: isRunning ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.85)',
              color: isRunning ? '#6366f1' : '#ffffff',
              fontSize: 13, fontWeight: 600, opacity: isRunning ? 0.8 : 1,
              transition: 'all 0.18s',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
            }}
          >
            {isRunning ? (
              <>
                <svg className="animate-spin" width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeDasharray="40 20"/>
                </svg>
                Running…
              </>
            ) : (
              <>
                <svg width="11" height="11" viewBox="0 0 11 11">
                  <polygon points="1,0.5 10.5,5.5 1,10.5" fill="currentColor"/>
                </svg>
                {isComplete ? 'Run Again' : 'Start Investigation'}
              </>
            )}
          </button>
        </div>
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
            {NAV.find(n => n.id === activeView)?.label}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {status === 'idle' && (
              <Chip color="#64748b" bg="var(--c-surface2)" border="var(--c-border)">Ready</Chip>
            )}
            {status === 'connecting' && (
              <Chip color="#6366f1" bg="#eef2ff" border="#c7d2fe">Connecting…</Chip>
            )}
            {isRunning && (
              <Chip color="#15803d" bg="var(--c-green-bg)" border="var(--c-green-border)" pulse>
                Investigating
              </Chip>
            )}
            {isComplete && (
              <Chip color="#1d4ed8" bg="#eff6ff" border="#bfdbfe">Complete</Chip>
            )}
            {isComplete && result && (
              <Chip
                color={result.evidence_sufficient ? '#15803d' : '#dc2626'}
                bg={result.evidence_sufficient ? 'var(--c-green-bg)' : 'var(--c-red-bg)'}
                border={result.evidence_sufficient ? 'var(--c-green-border)' : 'var(--c-red-border)'}
              >
                {result.evidence_sufficient ? '✓ Sufficient Evidence' : '✗ Insufficient Evidence'}
              </Chip>
            )}
          </div>
        </div>

        {/* Stats strip */}
        {isComplete && result && (
          <div style={{
            display: 'flex', gap: 10, padding: '10px 20px',
            background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)',
            overflowX: 'auto', flexShrink: 0,
          }}>
            {[
              { label: 'Steps',       value: result.iterations },
              { label: 'Duration',    value: `${result.total_time}s` },
              { label: 'Final Phase', value: result.phase },
              { label: 'Loops',       value: result.loop_count },
            ].map((s, i) => (
              <div key={i} style={{
                padding: '7px 14px', borderRadius: 8, flexShrink: 0,
                background: 'var(--c-surface2)', border: '1px solid var(--c-border)',
              }}>
                <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--c-text-dim)', fontWeight: 600, marginBottom: 2 }}>
                  {s.label}
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-text)' }}>{s.value}</div>
              </div>
            ))}
          </div>
        )}

        {/* View content */}
        <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
          {activeView === 'overview' && (
            <OverviewView
              activeNode={activeNode} phase={phase} nodeHistory={nodeHistory}
              isRunning={isRunning} initialClaims={initialClaims}
              events={events} logs={logs}
            />
          )}
          {activeView === 'dossier' && (
            <div style={{ height: '100%', overflow: 'auto', padding: 24 }}>
              <div style={{ maxWidth: 860, margin: '0 auto' }}>
                <DossierPanel dossier={dossier} findings={findings} isComplete={isComplete} />
              </div>
            </div>
          )}
          {activeView === 'network' && (
            <div style={{ height: '100%' }}>
              <NetworkGraph isComplete={isComplete} />
            </div>
          )}
          {activeView === 'activity' && (
            <div style={{ height: '100%' }}>
              <EventTimeline events={events} logs={logs} isRunning={isRunning} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Reusable chip component ────────────────────────────────────────────────
function Chip({ children, color, bg, border, pulse }) {
  return (
    <span style={{
      fontSize: 11, padding: '3px 10px', borderRadius: 20, fontWeight: 600,
      display: 'inline-flex', alignItems: 'center', gap: 5,
      color, background: bg, border: `1px solid ${border}`,
    }}>
      {pulse && (
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} className="animate-pulse" />
      )}
      {children}
    </span>
  )
}

// ── Overview: agent flow + live activity side by side ─────────────────────
function OverviewView({ activeNode, phase, nodeHistory, isRunning, initialClaims, events, logs }) {
  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {/* Left: Agent Flow */}
      <div style={{ width: '55%', borderRight: '1px solid var(--c-border)', display: 'flex', flexDirection: 'column' }}>
        <SectionHeader>Agent Flow</SectionHeader>
        <div style={{ flex: 1, background: 'var(--c-bg)' }}>
          <GraphView
            activeNode={activeNode} phase={phase}
            nodeHistory={nodeHistory} isRunning={isRunning}
            initialClaims={initialClaims}
          />
        </div>
      </div>
      {/* Right: Live Activity */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <EventTimeline events={events} logs={logs} isRunning={isRunning} />
      </div>
    </div>
  )
}

// ── Utility: section header strip ─────────────────────────────────────────
function SectionHeader({ children }) {
  return (
    <div style={{
      padding: '8px 16px', borderBottom: '1px solid var(--c-border)',
      background: 'var(--c-surface)', flexShrink: 0,
      fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
      letterSpacing: '0.06em', color: 'var(--c-text-dim)',
    }}>
      {children}
    </div>
  )
}

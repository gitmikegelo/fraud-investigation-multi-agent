import { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import GraphView from './GraphView'
import EventTimeline from './EventTimeline'
import { useInvestigation } from '../hooks/useInvestigation'

const PHASE_COLOR = {
  'Initializing':        '#a100ff',
  'Agent Orchestration': '#2962ff',
  'Investigating':       '#16a34a',
  'Compiling':           '#d97706',
  'Done':                '#16a34a',
  '—':                   '#94a3b8',
}

export default function AutoScan({ caseId, caseSummary, checklistContext, onBack, onNavigateToDossier }) {
  const {
    status, activeNode, phase, loopCount, events, logs,
    dossier, findings, result, startInvestigation, nodeHistory, elapsed,
  } = useInvestigation(caseId, checklistContext)

  const [showDossier, setShowDossier] = useState(false)
  const startedRef = useState(false)
  const [hasAutoNavigated, setHasAutoNavigated] = useState(false)

  const isRunning = status === 'running' || status === 'connecting'
  const isComplete = status === 'complete'
  const phaseColor = PHASE_COLOR[phase] || '#a100ff'
  const fmt = (s) => { const m = Math.floor(s / 60); return m > 0 ? `${m}m ${s % 60}s` : `${s}s` }

  // Auto-start on mount
  useEffect(() => {
    if (!startedRef[0] && caseId) {
      startedRef[1](true)
      startInvestigation()
    }
  }, [caseId])

  // Auto-navigate to dossier tab when complete
  useEffect(() => {
    if (isComplete && dossier && onNavigateToDossier && !hasAutoNavigated) {
      // Small delay so user sees the "Complete" status before switching
      const timer = setTimeout(() => {
        setHasAutoNavigated(true)
        onNavigateToDossier()
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [isComplete, dossier, onNavigateToDossier, hasAutoNavigated])
  // Reset auto-navigation state if a new case is loaded
  useEffect(() => {
    setHasAutoNavigated(false)
  }, [caseId])

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header bar */}
      <div style={{
        height: 50, flexShrink: 0, background: 'var(--c-surface)',
        borderBottom: '1px solid var(--c-border)',
        display: 'flex', alignItems: 'center', padding: '0 20px', gap: 12,
      }}>
        <button onClick={onBack} style={{
          background: 'transparent', border: '1px solid var(--c-border)', borderRadius: 6,
          color: 'var(--c-text-dim)', cursor: 'pointer', padding: '4px 10px', fontSize: 12,
        }}>← Copilot</button>

        <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--c-blue)', fontFamily: 'ui-monospace, monospace' }}>
          {caseId}
        </span>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-text)', flex: 1 }}>
          AI Fraud Analysis
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {status === 'idle' && (
            <Chip color="#64748b" bg="var(--c-surface2)" border="var(--c-border)">Ready</Chip>
          )}
          {status === 'connecting' && (
            <Chip color="var(--c-accent)" bg="var(--c-accent-light)" border="var(--c-accent-soft)">Connecting…</Chip>
          )}
          {isRunning && (
            <Chip color="#15803d" bg="var(--c-green-bg, rgba(34,197,94,0.1))" border="var(--c-green-border, rgba(34,197,94,0.3))" pulse>
              Investigating
            </Chip>
          )}
          {isComplete && (
            <Chip color="#1d4ed8" bg="#eff6ff" border="#bfdbfe">Complete</Chip>
          )}
          {isComplete && result && (
            <Chip
              color={result.evidence_sufficient ? '#15803d' : '#dc2626'}
              bg={result.evidence_sufficient ? 'var(--c-green-bg, rgba(34,197,94,0.1))' : 'var(--c-red-bg, rgba(239,68,68,0.1))'}
              border={result.evidence_sufficient ? 'var(--c-green-border, rgba(34,197,94,0.3))' : 'var(--c-red-border, rgba(239,68,68,0.3))'}
            >
              {result.evidence_sufficient ? '✓ Sufficient Evidence' : '✗ Insufficient Evidence'}
            </Chip>
          )}

          {isComplete && dossier && (
            <button onClick={() => setShowDossier(!showDossier)} style={{
              fontSize: 11, padding: '5px 14px', borderRadius: 'var(--r-btn)',
              border: '1px solid var(--c-accent)', background: 'transparent',
              color: 'var(--c-accent)', cursor: 'pointer', fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.03em',
            }}>
              {showDossier ? 'Show Graph' : 'View Dossier'}
            </button>
          )}
        </div>
      </div>

      {/* Status strip */}
      {(isRunning || isComplete) && (
        <div style={{
          display: 'flex', gap: 10, padding: '8px 20px',
          background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)',
          flexShrink: 0, alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
              background: isRunning ? '#22c55e' : '#475569',
              boxShadow: isRunning ? '0 0 0 2.5px rgba(34,197,94,0.25)' : 'none',
            }} className={isRunning ? 'animate-pulse' : ''} />
            <span style={{
              fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em',
              color: isRunning ? '#4ade80' : '#64748b',
            }}>
              {isRunning ? 'Live' : 'Complete'}
            </span>
          </div>
          <div style={{ fontSize: 12, color: phaseColor, fontWeight: 500 }}>{phase}</div>
          {loopCount > 0 && (
            <div style={{ fontSize: 11, color: '#475569' }}>
              Loop <span style={{ color: '#64748b', fontWeight: 600 }}>{loopCount}</span>
            </div>
          )}
          {elapsed > 0 && (
            <div style={{ fontSize: 11, color: '#475569', fontFamily: 'ui-monospace, monospace' }}>
              ⏱ {fmt(elapsed)}
            </div>
          )}

          {isComplete && result && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
              {[
                { label: 'Steps',       value: result.iterations },
                { label: 'Duration',    value: `${result.total_time}s` },
                { label: 'Loops',       value: result.loop_count },
              ].map((s, i) => (
                <div key={i} style={{
                  padding: '4px 10px', borderRadius: 6, flexShrink: 0,
                  background: 'var(--c-surface2)', border: '1px solid var(--c-border)',
                  fontSize: 10, color: 'var(--c-text)',
                }}>
                  <span style={{ color: 'var(--c-text-dim)', fontWeight: 600, marginRight: 4 }}>{s.label}</span>
                  <span style={{ fontWeight: 700 }}>{s.value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main content */}
      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
        {showDossier && dossier ? (
          <div style={{ height: '100%', overflow: 'auto', padding: 24 }}>
            <div style={{ maxWidth: 860, margin: '0 auto' }}>
              <div style={{
                background: 'var(--c-surface)', borderRadius: 'var(--r-card)',
                border: '1px solid var(--c-border)', padding: '24px 28px',
                boxShadow: 'var(--c-shadow-sm)',
              }}>
                <div className="chat-markdown">
                  <Markdown remarkPlugins={[remarkGfm]}>{dossier}</Markdown>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', height: '100%' }}>
            {/* Left: Agent Flow Graph */}
            <div style={{ width: '55%', borderRight: '1px solid var(--c-border)', display: 'flex', flexDirection: 'column' }}>
              <SectionHeader>Agent Flow</SectionHeader>
              <div style={{ flex: 1, background: 'var(--c-bg)' }}>
                <GraphView
                  activeNode={activeNode} phase={phase}
                  nodeHistory={nodeHistory} isRunning={isRunning}
                  loopCount={loopCount} elapsed={elapsed}
                  initialClaims={[]}
                />
              </div>
            </div>
            {/* Right: Live Activity */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <EventTimeline events={events} logs={logs} isRunning={isRunning} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

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

import { useState, useRef, useEffect, useCallback } from 'react'
import CaseQueue from './components/CaseQueue'
import ChecklistPanel from './components/ChecklistPanel'
import ChatPanel from './components/ChatPanel'
import InvestigationPanel from './components/InvestigationPanel'
import DossierPanel from './components/DossierPanel'
import { useCopilotChat } from './hooks/useCopilotChat'
import { ringColors } from './components/ChecklistSteps'

// ── Shared primitives ────────────────────────────────────────────────
export function Pill({ tone = 'plain', dot, children, style }) {
  const colors = {
    high:  { bg: 'var(--high-soft)',   color: 'var(--high)' },
    med:   { bg: 'var(--med-soft)',    color: 'var(--med)' },
    ok:    { bg: 'var(--low-soft)',    color: 'var(--low)' },
    acc:   { bg: 'var(--accent-soft)', color: 'var(--accent-ink)' },
    plain: { bg: 'var(--line-2)',      color: 'var(--ink-2)' },
  }
  const c = colors[tone] || colors.plain
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '3px 9px', borderRadius: 'var(--r-pill)',
      fontSize: 12.5, fontWeight: 500, whiteSpace: 'nowrap', alignSelf: 'start',
      background: c.bg, color: c.color, ...style,
    }}>
      {dot && <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'currentColor', flexShrink: 0, ...(dot === 'pulse' ? { animation: 'pulse 1.4s ease-in-out infinite' } : {}) }} />}
      {children}
    </span>
  )
}

// Same cutoffs as intelligence/risk_scoring_marine.py — the backend tier is the source of truth
export const riskLevel = (score) => (score >= 60 ? 'high' : score >= 30 ? 'med' : 'low')

export function RiskNumber({ score }) {
  const level = riskLevel(score)
  const color = level === 'high' ? 'var(--high)' : level === 'med' ? 'var(--med)' : 'var(--ink-2)'
  return <b style={{ fontWeight: 600, color }}>{score}</b>
}

export function RiskPill({ score }) {
  const level = riskLevel(score)
  const tone = level === 'high' ? 'high' : level === 'med' ? 'med' : 'plain'
  const label = level === 'high' ? 'High risk' : level === 'med' ? 'Medium risk' : 'Low risk'
  return <Pill tone={tone}>{label} · {score}</Pill>
}

// ── Icons ─────────────────────────────────────────────────────────────
const IconQueue = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
    <path d="M4 6h16M4 12h16M4 18h10"/>
  </svg>
)
const IconCheck = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 11l3 3 8-8M20 12v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1h11"/>
  </svg>
)
const IconChat = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 5h16v11H9l-5 4z"/>
  </svg>
)
const IconSearch = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/>
  </svg>
)
const IconFile = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 3h7l5 5v13H7zM14 3v5h5"/>
  </svg>
)
const IconBell = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
)

// ── Toast ─────────────────────────────────────────────────────────────
export function useToast() {
  const [toast, setToast] = useState(null)
  const timerRef = useRef(null)

  const showToast = useCallback((message, action) => {
    clearTimeout(timerRef.current)
    setToast({ message, action })
    timerRef.current = setTimeout(() => setToast(null), 4200)
  }, [])

  const Toast = toast ? (
    <div role="status" style={{
      position: 'fixed', bottom: 22, right: 22, zIndex: 60,
      background: 'var(--ink)', color: '#fff',
      padding: '10px 14px 10px 16px', borderRadius: 10,
      display: 'flex', alignItems: 'center', gap: 12,
      fontSize: 13.5, boxShadow: 'var(--sh-float)',
      animation: 'slide-up .25s ease',
    }}>
      {toast.message}
      {toast.action && (
        <button onClick={toast.action.onClick} style={{ color: '#D9B3FF', fontWeight: 500 }}>
          {toast.action.label}
        </button>
      )}
    </div>
  ) : null

  return { showToast, Toast }
}

// ── Case stepper ──────────────────────────────────────────────────────
function CaseStepper({ currentPage, checklistDone, investigationStatus, dossierReady, decision, onNavigate, checklistSteps }) {
  const passed = checklistSteps ? checklistSteps.filter(s => s.status === 'pass').length : 0
  const flagged = checklistSteps ? checklistSteps.filter(s => s.status === 'fail' || s.status === 'needs_review').length : 0
  const pageStep = currentPage === 'copilot' ? 'checklist' : currentPage

  const steps = [
    {
      key: 'checklist',
      label: 'Checklist',
      visual: !checklistSteps ? 'pending' : checklistDone ? 'done' : 'live',
      detail: !checklistSteps ? 'Not run' : checklistDone ? `${passed} passed · ${flagged} flagged` : 'Running 7 checks',
    },
    {
      key: 'investigation',
      label: 'Investigation',
      visual: investigationStatus === 'complete' ? 'done' : investigationStatus === 'running' ? 'live' : 'pending',
      detail: investigationStatus === 'complete' ? 'Complete' : investigationStatus === 'running' ? 'Agents working' : checklistDone && flagged ? 'Recommended' : 'Not started',
    },
    {
      key: 'dossier',
      label: 'Dossier',
      visual: dossierReady ? 'ready' : 'pending',
      detail: dossierReady ? 'Ready for review' : '—',
    },
    {
      key: 'decision',
      label: 'Decision',
      visual: decision ? 'done' : 'pending',
      detail: decision ? 'Decided' : dossierReady ? 'Yours to make' : 'Pending',
    },
  ]

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginTop: 18,
    }}>
      {steps.map((s, i) => {
        const isCur = s.key === pageStep
        const circleStyle = s.visual === 'done'
          ? { background: 'var(--low)', ...ringColors('var(--low)'), color: '#fff' }
          : s.visual === 'live'
          ? { ...ringColors('var(--accent)', 'transparent'), animation: 'spin .9s linear infinite', background: 'transparent', color: 'var(--accent-ink)' }
          : s.visual === 'ready'
          ? { background: 'var(--accent)', ...ringColors('var(--accent)'), color: '#fff' }
          : { background: '#fff', ...ringColors('var(--line)'), color: 'var(--muted)' }

        return (
          <button key={s.key} onClick={() => onNavigate(s.key)} style={{
            display: 'flex', alignItems: 'center', gap: 10, textAlign: 'left',
            padding: '10px 12px', borderRadius: 'var(--r-m)',
            background: isCur ? '#fff' : 'rgba(255,255,255,.6)',
            border: isCur ? '1px solid var(--accent)' : '1px solid rgba(227,208,250,.8)',
            boxShadow: isCur ? 'var(--sh-focus)' : 'none',
            cursor: 'pointer',
          }}>
            <div style={{
              width: 22, height: 22, borderRadius: '50%',
              display: 'grid', placeItems: 'center',
              fontSize: 11.5, fontWeight: 600,
              borderWidth: 1.5, borderStyle: 'solid',
              flexShrink: 0,
              ...circleStyle,
            }}>
              {s.visual === 'done' ? '✓' : s.visual === 'ready' ? i + 1 : i + 1}
            </div>
            <div>
              <b style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>{s.label}</b>
              <small style={{
                display: 'block', fontSize: 12,
                color: s.visual === 'live' ? 'var(--accent-ink)' : 'var(--muted)',
                lineHeight: 1.3,
              }}>{s.detail}</small>
            </div>
          </button>
        )
      })}
    </div>
  )
}

// ── Sidebar nav button ────────────────────────────────────────────────
function NavBtn({ active, icon, label, meta, metaType, onClick }) {
  return (
    <button
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 10px', borderRadius: 'var(--r-s)',
        color: active ? 'var(--accent-ink)' : 'var(--ink-2)',
        fontWeight: 500, textAlign: 'left', width: '100%',
        background: active ? 'var(--accent-soft)' : 'transparent',
        position: 'relative', transition: 'background .15s',
        fontSize: 13.5,
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--canvas)' }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
    >
      {active && (
        <span style={{
          position: 'absolute', left: -12, top: 8, bottom: 8,
          width: 3, borderRadius: '0 3px 3px 0', background: 'var(--accent)',
        }} />
      )}
      {icon}
      <span style={{ flex: 1 }}>{label}</span>
      {meta && metaType === 'live' ? (
        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--accent-ink)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1.4s ease-in-out infinite' }} />
          {meta}
        </span>
      ) : meta ? (
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted)' }}>{meta}</span>
      ) : null}
    </button>
  )
}

// ── Main App ──────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState('queue') // queue | checklist | copilot | investigation | dossier
  const [selectedClaim, setSelectedClaim] = useState(null)
  const [claimCount, setClaimCount] = useState(null)

  // Shared investigation state (lifted up so switching pages preserves it)
  const [investigationStatus, setInvestigationStatus] = useState('idle')
  const investigationDone = investigationStatus === 'complete'
  const [dossierMarkdown, setDossierMarkdown] = useState(null)
  const [decision, setDecision] = useState(null)
  const [investigationRequest, setInvestigationRequest] = useState(0)

  const { showToast, Toast } = useToast()

  // One chat socket per open claim, shared by the Checklist and Copilot pages
  const chat = useCopilotChat(selectedClaim?.case_id)
  const checklistSteps = chat.checklistState?.steps || null
  const checklistDone = !!chat.checklistState?.summary
  const clearChat = chat.clearMessages

  const wasDone = useRef(false)
  useEffect(() => {
    if (checklistDone && !wasDone.current && selectedClaim) {
      showToast(`Checklist finished for ${selectedClaim.case_id}`, {
        label: 'See results',
        onClick: () => setPage('copilot'),
      })
    }
    wasDone.current = checklistDone
  }, [checklistDone, selectedClaim, showToast])

  // Fetch claim count for sidebar
  useEffect(() => {
    fetch('/api/claims?date_range=all')
      .then(r => r.json())
      .then(d => setClaimCount((d.claims || []).length))
      .catch(() => {})
  }, [])

  const openClaim = useCallback((claim) => {
    const same = claim.case_id === selectedClaim?.case_id
    if (!same) {
      clearChat()
      setInvestigationStatus('idle')
      setDossierMarkdown(null)
      setDecision(null)
    }
    setSelectedClaim(claim)
    setPage(same && checklistDone ? 'copilot' : 'checklist')
  }, [selectedClaim?.case_id, clearChat, checklistDone])

  const goTo = useCallback((p) => setPage(p === 'decision' ? 'dossier' : p === 'checklist' && checklistDone ? 'copilot' : p), [checklistDone])

  const handleInvestigationComplete = useCallback((dossier) => {
    setDossierMarkdown(dossier)
    showToast(`Dossier ready for ${selectedClaim?.case_id}`, {
      label: 'Review',
      onClick: () => setPage('dossier'),
    })
  }, [selectedClaim, showToast])

  const handleDecision = useCallback((action) => {
    const labels = { decline: 'Declined', approve: 'Approved', siu: 'Referred for investigation', survey: 'Independent survey requested' }
    if (action !== 'survey') setDecision(action)
    showToast(`${labels[action] || 'Decision recorded'} · ${selectedClaim?.case_id}`)
  }, [selectedClaim, showToast])

  // Compute sidebar meta for claim items
  const checklistMeta = !checklistSteps ? null : checklistDone ? 'Done' : `${checklistSteps.filter(s => ['pass', 'fail', 'needs_review'].includes(s.status)).length}/7`
  const investigationMeta = investigationDone ? 'Done' : investigationStatus === 'running' ? 'Live' : null
  const dossierMeta = dossierMarkdown ? 'Ready' : null

  // Breadcrumb
  const pageLabels = { queue: 'Queue', checklist: 'Checklist', copilot: 'Copilot', investigation: 'Investigation', dossier: 'Dossier' }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'var(--sidebar-w) 1fr', minHeight: '100vh' }}>

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <aside style={{
        background: 'var(--surface)', borderRight: '1px solid var(--line)',
        padding: '18px 12px', display: 'flex', flexDirection: 'column', gap: 20,
        position: 'sticky', top: 0, height: '100vh', overflowY: 'auto',
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px' }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
            background: 'var(--grad-brand)', display: 'grid', placeItems: 'center',
            boxShadow: '0 4px 12px -6px rgba(161,0,255,.5)',
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 11l3.5-4 3 3L14 4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <b style={{ fontSize: 14.5, fontWeight: 600, letterSpacing: '-.01em', display: 'block' }}>Claims Co-Pilot</b>
            <span style={{ display: 'block', fontSize: 12, color: 'var(--muted)' }}>Marine cargo</span>
          </div>
        </div>

        {/* Workspace nav */}
        <nav aria-label="Workspace" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <NavBtn
            active={page === 'queue' && !selectedClaim}
            icon={<IconQueue />}
            label="Queue"
            meta={claimCount != null ? String(claimCount) : ''}
            onClick={() => { setSelectedClaim(null); setPage('queue') }}
          />
        </nav>

        {/* Claim group */}
        {selectedClaim && (
          <div style={{ borderTop: '1px solid var(--line-2)', paddingTop: 16 }}>
            <div style={{ fontSize: 12, color: 'var(--muted)', padding: '0 10px 6px', display: 'flex', gap: 8, minWidth: 0 }}>
              <b style={{ color: 'var(--ink)', fontWeight: 600, whiteSpace: 'nowrap' }}>{selectedClaim.case_id}</b>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedClaim.subject_name}</span>
            </div>
            <nav aria-label="Current claim" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <NavBtn
                active={page === 'checklist'}
                icon={<IconCheck />}
                label="Checklist"
                meta={checklistMeta}
                onClick={() => setPage('checklist')}
              />
              <NavBtn
                active={page === 'copilot'}
                icon={<IconChat />}
                label="Copilot"
                onClick={() => setPage('copilot')}
              />
              <NavBtn
                active={page === 'investigation'}
                icon={<IconSearch />}
                label="Investigation"
                meta={investigationMeta}
                metaType={investigationStatus === 'running' ? 'live' : undefined}
                onClick={() => setPage('investigation')}
              />
              <NavBtn
                active={page === 'dossier'}
                icon={<IconFile />}
                label="Dossier"
                meta={dossierMeta}
                onClick={() => setPage('dossier')}
              />
            </nav>
          </div>
        )}

        {/* User — pinned bottom */}
        <div style={{ marginTop: 'auto', display: 'flex', gap: 10, alignItems: 'center', padding: '4px 8px', fontSize: 13 }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
            background: 'var(--accent-soft)', color: 'var(--accent-ink)',
            display: 'grid', placeItems: 'center', fontWeight: 600, fontSize: 12,
          }}>MA</div>
          <div>
            <div style={{ fontWeight: 500 }}>Mike Arsolon</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>AI Engineer</div>
          </div>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────────────── */}
      <main style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>

        {/* Top bar */}
        <div style={{
          height: 'var(--topbar-h)', display: 'flex', alignItems: 'center', gap: 14,
          padding: '0 var(--gutter)', position: 'sticky', top: 0, zIndex: 20,
          background: 'rgba(251,246,255,.97)', backdropFilter: 'blur(10px)',
          borderBottom: '1px solid rgba(227,208,250,.6)',
          flexShrink: 0,
        }}>
          {/* Breadcrumbs */}
          <nav aria-label="Breadcrumbs" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--muted)' }}>
            <button
              onClick={() => { setSelectedClaim(null); setPage('queue') }}
              style={{ color: 'var(--muted)', padding: '2px 4px', borderRadius: 4 }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--ink)'; e.currentTarget.style.background = 'rgba(0,0,0,.04)' }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--muted)'; e.currentTarget.style.background = 'transparent' }}
            >Queue</button>
            {selectedClaim && (
              <>
                <span>/</span>
                <button
                  onClick={() => setPage('checklist')}
                  style={{ color: 'var(--muted)', padding: '2px 4px', borderRadius: 4 }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--ink)'; e.currentTarget.style.background = 'rgba(0,0,0,.04)' }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--muted)'; e.currentTarget.style.background = 'transparent' }}
                >{selectedClaim.case_id}</button>
                <span>/</span>
                <b aria-current="page" style={{ color: 'var(--ink)', fontWeight: 600, padding: '2px 4px' }}>
                  {pageLabels[page] || page}
                </b>
              </>
            )}
          </nav>

          {/* Search — cosmetic */}
          <div style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8,
            border: '1px solid var(--accent-line)', borderRadius: 'var(--r-s)',
            padding: '6px 10px', width: 280, color: 'var(--muted)', fontSize: 13,
            background: 'rgba(255,255,255,.85)',
          }}>
            <IconSearch />
            <span style={{ flex: 1 }}>Search claims, consignees, surveyors</span>
            <span style={{
              display: 'inline-block', border: '1px solid var(--line)', borderRadius: 4,
              padding: '0 5px', fontSize: 11, background: 'var(--surface)', lineHeight: '18px',
            }}>⌘K</span>
          </div>

          {/* Bell */}
          <button style={{
            position: 'relative', width: 34, height: 34, display: 'grid', placeItems: 'center',
            borderRadius: 8, color: 'var(--ink-2)',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,.04)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <IconBell />
            {dossierMarkdown && (
              <span style={{
                position: 'absolute', top: 7, right: 8, width: 7, height: 7,
                borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 0 2px #FBF6FF',
              }} />
            )}
          </button>
        </div>

        {/* Pages */}
        <div style={{ flex: 1, overflow: 'auto' }}>

          {/* Queue page */}
          <div style={{ display: page === 'queue' ? 'block' : 'none', height: '100%' }}>
            <CaseQueue active={page === 'queue'} onOpenClaim={openClaim} />
          </div>

          {/* Claim pages */}
          {selectedClaim && (
            <>
              {/* Hero band — shown on all claim pages */}
              <div style={{ display: page !== 'queue' ? 'block' : 'none' }}>
                {/* Hero */}
                <div style={{
                  padding: '24px var(--gutter) 20px',
                  background: 'var(--grad-hero)',
                  position: 'relative',
                }}>
                  <div style={{
                    position: 'absolute', left: 0, right: 0, bottom: 0, height: 1,
                    background: 'linear-gradient(90deg, transparent, rgba(161,0,255,.2), transparent)',
                  }} />
                  {/* Row 1 */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    <div style={{ flex: 1 }}>
                      <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-.02em' }}>
                        {selectedClaim.case_id}{' '}
                        <span style={{ fontWeight: 500, color: 'var(--ink-2)' }}>{selectedClaim.subject_name}</span>
                      </h1>
                      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>
                        {selectedClaim.employer_name && <span><b style={{ color: 'var(--ink-2)', fontWeight: 500 }}>{selectedClaim.employer_name}</b></span>}
                        {selectedClaim.claim_type && <span>{({ breakage: 'Breakage', wet_damage: 'Wet damage', contamination: 'Contamination', shortage: 'Shortage', theft_pilferage: 'Theft / pilferage' })[selectedClaim.claim_type] || selectedClaim.claim_type}</span>}
                        {selectedClaim.claim_amount > 0 && <span>Claimed <b style={{ color: 'var(--ink-2)', fontWeight: 500 }}>US${(selectedClaim.claim_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}</b></span>}
                        {selectedClaim.provider_name && <span>Surveyor: {selectedClaim.provider_name}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                      <RiskPill score={selectedClaim.risk_score || 0} />
                    </div>
                  </div>

                  {/* Case stepper */}
                  <CaseStepper
                    currentPage={page}
                    checklistDone={checklistDone}
                    investigationStatus={investigationStatus}
                    decision={decision}
                    dossierReady={!!dossierMarkdown}
                    checklistSteps={checklistSteps}
                    onNavigate={goTo}
                  />
                </div>

                {/* Checklist page */}
                <div style={{ display: page === 'checklist' ? 'block' : 'none', padding: 'var(--gutter)' }}>
                  <ChecklistPanel
                    claim={selectedClaim}
                    chat={chat}
                    onGoToCopilot={() => setPage('copilot')}
                  />
                </div>

                {/* Copilot page */}
                <div style={{ display: page === 'copilot' ? 'block' : 'none', padding: 'var(--gutter)' }}>
                  <ChatPanel
                    chat={chat}
                    onStartInvestigation={() => { setInvestigationRequest(n => n + 1); setPage('investigation') }}
                    onDecision={handleDecision}
                    showToast={showToast}
                  />
                </div>

                {/* Investigation page */}
                <div style={{ display: page === 'investigation' ? 'block' : 'none', padding: 'var(--gutter)' }}>
                  <InvestigationPanel
                    key={selectedClaim.case_id}
                    claim={selectedClaim}
                    startRequest={investigationRequest}
                    onComplete={handleInvestigationComplete}
                    onStatus={setInvestigationStatus}
                    showToast={showToast}
                  />
                </div>

                {/* Dossier page */}
                <div style={{ display: page === 'dossier' ? 'block' : 'none', padding: 'var(--gutter)' }}>
                  <DossierPanel
                    key={selectedClaim.case_id}
                    claim={selectedClaim}
                    dossierMarkdown={dossierMarkdown}
                    investigationDone={investigationDone}
                    decision={decision}
                    onDecision={handleDecision}
                    onGoToInvestigation={() => setPage('investigation')}
                  />
                </div>
              </div>
            </>
          )}

          {/* No claim selected on a claim page */}
          {!selectedClaim && page !== 'queue' && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
              Select a claim from the queue to continue.
            </div>
          )}
        </div>
      </main>

      {Toast}
    </div>
  )
}

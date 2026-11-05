import { useState, useEffect, useCallback, useRef } from 'react'
import { RiskNumber, Pill, riskLevel } from '../App'

// ── Helpers ───────────────────────────────────────────────────────────
function riskTone(score) {
  const l = riskLevel(score)
  return l === 'high' ? 'high' : l === 'med' ? 'med' : 'plain'
}

const openTasks = (claim) => (claim.workflow_tasks || []).filter(t => t.status !== 'completed')

// "Today" is the queue's own business date (latest filing), so the demo reads the same on any day
function dueLabel(claim, today) {
  const dates = openTasks(claim).map(t => t.due_date).filter(Boolean).sort()
  if (!dates.length || !today) return { text: '—', late: false }
  const diff = Math.round((new Date(dates[0]) - new Date(today)) / 86400000)
  if (diff < 0) return { text: 'Overdue', late: true }
  if (diff === 0) return { text: 'Today', late: true }
  if (diff === 1) return { text: 'Tomorrow', late: false }
  return { text: `${diff} days`, late: false }
}

const usd = (n) => `US$${(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

function flagReasons(claim) {
  return [...(claim.rules_triggered || [])]
    .sort((a, b) => (a.severity === 'BLOCK' ? 0 : 1) - (b.severity === 'BLOCK' ? 0 : 1))
    .slice(0, 3)
    .map(r => ({ severity: r.severity === 'BLOCK' ? 'high' : 'medium', text: (r.explanation || r.rule_name || '').split(' — ')[0] }))
}

const TYPE_LABELS = {
  breakage:        'Breakage',
  wet_damage:      'Wet damage',
  contamination:   'Contamination',
  shortage:        'Shortage',
  theft_pilferage: 'Theft / pilferage',
}

const STATE_MAP = {
  new:       { label: 'New',            tone: 'plain' },
  open:      { label: 'New',            tone: 'plain' },
  reviewing: { label: 'Checklist done', tone: 'plain' },
  investigating: { label: 'Investigating', tone: 'acc', pulse: true },
  dossier_ready: { label: 'Dossier ready', tone: 'plain' },
  closed:    { label: 'Closed',         tone: 'plain' },
}

function statePill(status) {
  const cfg = STATE_MAP[status] || { label: status || 'New', tone: 'plain' }
  return <Pill tone={cfg.tone} dot={cfg.pulse ? 'pulse' : undefined}>{cfg.label}</Pill>
}

// ── Preview panel ─────────────────────────────────────────────────────
function PreviewPanel({ claim, today, onOpen }) {
  if (!claim) return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--line)', borderTop: '3px solid var(--accent)',
      borderRadius: 'var(--r-l)', padding: '40px 20px 20px',
      color: 'var(--muted)', fontSize: 13, textAlign: 'center',
    }}>
      Select a claim to preview
    </div>
  )

  const due = dueLabel(claim, today)
  const reasons = flagReasons(claim)
  const m = claim.key_metrics || {}

  return (
    <div aria-live="polite" style={{
      background: 'var(--surface)', border: '1px solid var(--line)', borderTop: '3px solid var(--accent)',
      borderRadius: 'var(--r-l)', padding: 20, position: 'sticky', top: 76,
    }}>
      {/* Risk + due */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Pill tone={riskTone(claim.risk_score)}>
          {riskLevel(claim.risk_score) === 'high' ? 'High risk' : riskLevel(claim.risk_score) === 'med' ? 'Medium risk' : 'Low risk'} · {claim.risk_score}
        </Pill>
        {due.text !== '—' && (
          <span style={{ marginLeft: 'auto', fontSize: 13, color: due.late ? 'var(--high)' : 'var(--muted)', fontWeight: due.late ? 500 : 400 }}>
            Due {due.text.toLowerCase()}
          </span>
        )}
      </div>

      {/* Title */}
      <h2 style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-.01em', marginTop: 12 }}>
        {claim.case_id} · {claim.subject_name}
      </h2>
      <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>
        {m.shipment || claim.employer_name} · {TYPE_LABELS[claim.claim_type] || claim.claim_type}
      </div>

      {/* Key-value */}
      <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 16px', margin: '16px 0', fontSize: 13 }}>
        {[
          ['Claimed', claim.claim_amount > 0 && usd(claim.claim_amount)],
          ['B/L', m.bl_number],
          ['Surveyor', claim.provider_name],
          ['Filed', claim.date_filed],
        ].filter(([, v]) => v).map(([k, v]) => (
          <div key={k} style={{ display: 'contents' }}>
            <dt style={{ color: 'var(--muted)' }}>{k}</dt>
            <dd style={{ textAlign: 'right', fontWeight: 500 }}>{v}</dd>
          </div>
        ))}
      </dl>

      {/* Why flagged */}
      {reasons.length > 0 && (
        <div style={{ borderTop: '1px solid var(--line)', paddingTop: 14 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Why it's flagged</h3>
          <ul style={{ listStyle: 'none' }}>
            {reasons.map((r, i) => (
              <li key={i} style={{ display: 'flex', gap: 10, padding: '5px 0', fontSize: 13, color: 'var(--ink-2)' }}>
                <i style={{
                  width: 6, height: 6, borderRadius: '50%', flexShrink: 0, marginTop: 7,
                  background: r.severity === 'high' ? 'var(--high)' : 'var(--med)',
                }} />
                {r.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        <button onClick={() => onOpen(claim)} style={{
          flex: 1, padding: '8px 14px', borderRadius: 'var(--r-s)',
          background: 'var(--grad-primary)', color: '#fff', fontWeight: 500,
          border: '1px solid var(--accent)', boxShadow: 'var(--sh-btn)', fontSize: 13.5,
        }}>
          Open claim
        </button>
      </div>
    </div>
  )
}

// ── CaseQueue ─────────────────────────────────────────────────────────
export default function CaseQueue({ active, onOpenClaim }) {
  const [allClaims, setAllClaims] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dateTab, setDateTab] = useState('all')
  const [typeTab, setTypeTab] = useState(null)
  const [riskFilter, setRiskFilter] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [checkedIds, setCheckedIds] = useState(new Set())
  const rowRefs = useRef({})

  const fetchClaims = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ date_range: dateTab })
      if (typeTab) params.set('claim_type', typeTab)
      const res = await fetch(`/api/claims?${params}`)
      if (!res.ok) throw new Error('Network error')
      const data = await res.json()
      const sorted = (data.claims || []).sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))
      setAllClaims(sorted)
      setSelectedId(prev => (prev && sorted.some(c => c.case_id === prev)) ? prev : sorted[0]?.case_id ?? null)
    } catch {
      setError("Couldn't load the queue.")
    } finally {
      setLoading(false)
    }
  }, [dateTab, typeTab])

  useEffect(() => { fetchClaims() }, [fetchClaims])

  const LEVEL = { HIGH: 'high', MEDIUM: 'med', LOW: 'low' }
  const claims = riskFilter ? allClaims.filter(c => riskLevel(c.risk_score || 0) === LEVEL[riskFilter]) : allClaims
  const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 }
  allClaims.forEach(c => { counts[{ high: 'HIGH', med: 'MEDIUM', low: 'LOW' }[riskLevel(c.risk_score || 0)]]++ })
  const today = allClaims.map(c => c.date_filed).filter(Boolean).sort().at(-1)

  // Keyboard navigation (queue page only, never while typing)
  useEffect(() => {
    if (!active) return
    function onKey(e) {
      if (['input', 'textarea', 'button'].includes(e.target.tagName.toLowerCase())) return
      const filtered = claims
      const idx = selectedId != null ? filtered.findIndex(c => c.case_id === selectedId) : -1
      if (e.key === 'j' || e.key === 'J') {
        const next = filtered[Math.min(idx + 1, filtered.length - 1)]
        if (next) setSelectedId(next.case_id)
      } else if (e.key === 'k' || e.key === 'K') {
        const prev = filtered[Math.max(idx - 1, 0)]
        if (prev) setSelectedId(prev.case_id)
      } else if ((e.key === 'x' || e.key === 'X') && selectedId) {
        setCheckedIds(prev => {
          const s = new Set(prev)
          if (s.has(selectedId)) s.delete(selectedId)
          else s.add(selectedId)
          return s
        })
      } else if (e.key === 'Enter' && selectedId) {
        const claim = filtered.find(c => c.case_id === selectedId)
        if (claim) onOpenClaim(claim)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active, claims, selectedId, onOpenClaim])

  const selectedClaim = claims.find(c => c.case_id === selectedId) || null

  const dateTabs = [
    { id: 'today',     label: 'Today' },
    { id: 'this_week', label: 'This week' },
    { id: 'all',       label: 'All' },
  ]
  const typeTabs = [
    { id: null,               label: 'All types' },
    { id: 'breakage',        label: 'Breakage' },
    { id: 'wet_damage',      label: 'Wet damage' },
    { id: 'contamination',   label: 'Contamination' },
    { id: 'shortage',        label: 'Shortage' },
    { id: 'theft_pilferage', label: 'Theft / pilferage' },
  ]

  const riskTiles = [
    { key: 'HIGH',   label: 'High',   n: counts.HIGH,   color: 'var(--high)',      pip: '#C22F3A' },
    { key: 'MEDIUM', label: 'Medium', n: counts.MEDIUM, color: 'var(--med-bar)',   pip: '#E0A43A' },
    { key: 'LOW',    label: 'Low',    n: counts.LOW,    color: 'var(--neutral-risk)', pip: '#A09CB0' },
  ]

  return (
    <div>
      {/* Hero */}
      <div style={{
        padding: '24px var(--gutter) 20px', position: 'relative',
        background: 'var(--grad-hero)',
      }}>
        <div style={{
          position: 'absolute', left: 0, right: 0, bottom: 0, height: 1,
          background: 'linear-gradient(90deg, transparent, rgba(161,0,255,.2), transparent)',
        }} />
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-.02em' }}>Marine cargo claims queue</h1>
            <p style={{ color: 'var(--muted)', marginTop: 3, fontSize: 13.5 }}>
              {allClaims.length} open · sorted by risk{today ? ` · business date ${today}` : ''}
            </p>
          </div>
          <button onClick={fetchClaims} style={{
            padding: '8px 14px', borderRadius: 'var(--r-s)', fontSize: 13, fontWeight: 500,
            border: '1px solid var(--accent-line)', background: 'rgba(255,255,255,.75)',
            color: 'var(--ink-2)',
          }}>Refresh</button>
        </div>

        {/* Risk tiles */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 220px))', gap: 10, marginTop: 18 }}>
          {riskTiles.map(t => (
            <button key={t.key} onClick={() => setRiskFilter(riskFilter === t.key ? null : t.key)}
              aria-pressed={riskFilter === t.key}
              style={{
                background: riskFilter === t.key ? '#fff' : 'rgba(255,255,255,.72)',
                border: riskFilter === t.key ? '1px solid var(--accent)' : '1px solid #ECE1F9',
                boxShadow: riskFilter === t.key ? 'var(--sh-focus)' : 'none',
                borderRadius: 12, padding: '12px 16px', textAlign: 'left',
                display: 'flex', alignItems: 'baseline', gap: 10, cursor: 'pointer',
              }}>
              <span style={{ width: 9, height: 9, borderRadius: 3, background: t.pip, alignSelf: 'center', flexShrink: 0 }} />
              <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: '-.02em', color: t.color }}>{t.n}</span>
              <span style={{ color: 'var(--muted)', fontSize: 13 }}>{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Toolbar */}
      <div style={{ padding: '12px var(--gutter) 0', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {/* Date segmented control */}
        <div style={{ display: 'inline-flex', background: '#E9E6F0', borderRadius: 8, padding: 3 }}>
          {dateTabs.map(t => (
            <button key={t.id} onClick={() => setDateTab(t.id)} style={{
              padding: '5px 12px', borderRadius: 6, fontWeight: 500, fontSize: 13,
              color: dateTab === t.id ? 'var(--accent-ink)' : 'var(--ink-2)',
              background: dateTab === t.id ? 'var(--surface)' : 'transparent',
              boxShadow: dateTab === t.id ? '0 1px 2px rgba(16,24,40,.08)' : 'none',
            }}>{t.label}</button>
          ))}
        </div>

        {/* Type chips */}
        {typeTabs.map(t => (
          <button key={t.id || 'all'} onClick={() => setTypeTab(t.id)} style={{
            padding: '5px 11px', border: '1px solid', borderRadius: 'var(--r-pill)',
            fontSize: 13, cursor: 'pointer',
            borderColor: typeTab === t.id ? 'var(--accent-line)' : 'var(--line)',
            color: typeTab === t.id ? 'var(--accent-ink)' : 'var(--ink-2)',
            background: typeTab === t.id ? 'var(--accent-soft)' : 'var(--surface)',
          }}>{t.label}</button>
        ))}

        <span style={{ marginLeft: 'auto', fontSize: 13, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
          Risk, high first
        </span>
      </div>

      {/* Main layout: table + preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) var(--preview-w)', gap: 18, padding: 'var(--gutter)', alignItems: 'start' }}>
        {/* Table panel */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-l)', overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Loading claims…</div>
          ) : error ? (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>{error}</p>
              <button onClick={fetchClaims} style={{
                padding: '8px 16px', borderRadius: 'var(--r-s)', border: '1px solid var(--line)',
                background: 'var(--surface)', color: 'var(--ink-2)', fontSize: 13,
              }}>Retry</button>
            </div>
          ) : (
            <>
              {/* Header row */}
              <div role="row" style={{
                display: 'grid',
                gridTemplateColumns: '24px 100px minmax(130px,1.4fr) 70px 80px 60px 124px',
                gap: 12, padding: '10px 16px',
                color: 'var(--muted)', fontSize: 12.5, fontWeight: 500,
                background: '#FAF9FC', borderBottom: '1px solid var(--line-2)',
              }}>
                <span />
                <span>Claim</span>
                <span>Claimant / Shipment</span>
                <span>Signals</span>
                <span>Due</span>
                <span style={{ color: 'var(--ink)', display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                  Risk ↓
                </span>
                <span>State</span>
              </div>

              {/* Rows */}
              {claims.length === 0 ? (
                <div style={{ padding: '40px 16px', textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
                  No claims match these filters.{' '}
                  <button onClick={() => { setRiskFilter(null); setTypeTab(null) }} style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
                    Clear filters
                  </button>
                </div>
              ) : (
                <div role="grid" aria-label="Claims queue">
                  {claims.map(c => {
                    const isSel = c.case_id === selectedId
                    const isChk = checkedIds.has(c.case_id)
                    const due = dueLabel(c, today)
                    const ruleCount = (c.rules_triggered || []).length
                    const taskCount = openTasks(c).length

                    return (
                      <div
                        key={c.case_id}
                        ref={el => rowRefs.current[c.case_id] = el}
                        role="row"
                        aria-selected={isSel}
                        onClick={() => setSelectedId(c.case_id)}
                        onDoubleClick={() => onOpenClaim(c)}
                        onKeyDown={e => { if (e.key === 'Enter') onOpenClaim(c) }}
                        tabIndex={0}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '24px 100px minmax(130px,1.4fr) 70px 80px 60px 124px',
                          gap: 12, padding: '11px 16px',
                          borderBottom: '1px solid var(--line-2)', cursor: 'pointer',
                          position: 'relative',
                          background: isSel ? '#FAF5FF' : 'transparent',
                          boxShadow: isSel ? 'inset 3px 0 0 var(--accent)' : 'none',
                        }}
                        onMouseEnter={e => { if (!isSel) e.currentTarget.style.background = '#FBFAFD' }}
                        onMouseLeave={e => { if (!isSel) e.currentTarget.style.background = 'transparent' }}
                      >
                        {/* Checkbox */}
                        <div
                          role="checkbox"
                          aria-checked={isChk}
                          onClick={e => {
                            e.stopPropagation()
                            setCheckedIds(prev => {
                              const s = new Set(prev)
                              if (s.has(c.case_id)) s.delete(c.case_id)
                              else s.add(c.case_id)
                              return s
                            })
                          }}
                          style={{
                            width: 16, height: 16, border: isChk ? 'none' : '1.5px solid #C8C4D3',
                            borderRadius: 4, display: 'grid', placeItems: 'center',
                            background: isChk ? 'var(--accent)' : '#fff', alignSelf: 'center', flexShrink: 0,
                            cursor: 'pointer',
                          }}
                        >
                          {isChk && (
                            <svg width="10" height="7" viewBox="0 0 10 7" fill="none">
                              <path d="M1 3.5l3 3 5-5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                          )}
                        </div>

                        {/* Claim ID */}
                        <div style={{ alignSelf: 'center' }}>
                          <div style={{ fontWeight: 600, fontSize: 13.5 }}>{c.case_id}</div>
                          <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                            {TYPE_LABELS[c.claim_type] || (c.claim_type || '').replace(/_/g,' ')}
                          </div>
                        </div>

                        {/* Claimant / shipment */}
                        <div style={{ alignSelf: 'center', minWidth: 0 }}>
                          <div style={{ fontWeight: 500, fontSize: 13.5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {c.subject_name}
                          </div>
                          <div style={{ color: 'var(--muted)', fontSize: 13, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {c.employer_name || '—'}
                          </div>
                        </div>

                        {/* Signals */}
                        <div style={{ alignSelf: 'center', display: 'flex', gap: 10, color: 'var(--ink-2)', fontSize: 13 }}>
                          {ruleCount > 0 && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }} title={`${ruleCount} rules triggered`}>
                              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M5 21V4h11l-2 4 2 4H5"/></svg>
                              {ruleCount}
                            </span>
                          )}
                          {taskCount > 0 && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }} title={`${taskCount} open tasks`}>
                              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 9h6M9 13h6"/></svg>
                              {taskCount}
                            </span>
                          )}
                          {ruleCount === 0 && taskCount === 0 && <span style={{ color: 'var(--muted)' }}>—</span>}
                        </div>

                        {/* Due */}
                        <div style={{
                          alignSelf: 'center', fontSize: 13,
                          color: due.late ? 'var(--high)' : 'var(--ink-2)',
                          fontWeight: due.late ? 500 : 400,
                        }}>
                          {due.text}
                        </div>

                        {/* Risk number */}
                        <div style={{ alignSelf: 'center' }}>
                          <RiskNumber score={c.risk_score || 0} />
                        </div>

                        {/* State pill */}
                        <div style={{ alignSelf: 'center' }}>
                          {statePill(c.status)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Footer */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 16px', borderTop: '1px solid var(--line-2)',
                fontSize: 12.5, color: 'var(--muted)', background: '#FAF9FC',
              }}>
                <span>J K move · Enter open · X select</span>
                <span style={{ marginLeft: 'auto' }}>Showing {claims.length} of {allClaims.length}</span>
              </div>
            </>
          )}
        </div>

        {/* Preview panel */}
        <PreviewPanel claim={selectedClaim} today={today} onOpen={onOpenClaim} />
      </div>

      {/* Bulk bar */}
      {checkedIds.size > 0 && (
        <div style={{
          position: 'sticky', bottom: 18, marginLeft: 'var(--gutter)',
          display: 'flex', alignItems: 'center', gap: 10,
          background: 'var(--ink)', color: '#fff', borderRadius: 12,
          padding: '10px 12px 10px 18px', boxShadow: 'var(--sh-float)',
          width: 'fit-content',
        }}>
          <span style={{ fontWeight: 500, fontSize: 13.5 }}>{checkedIds.size} selected</span>
          <button style={{
            padding: '5px 10px', borderRadius: 'var(--r-s)', fontSize: 13, fontWeight: 500,
            background: 'rgba(255,255,255,.08)', border: '1px solid rgba(255,255,255,.16)', color: '#fff',
          }}>Run checklist</button>
          <button style={{
            padding: '5px 10px', borderRadius: 'var(--r-s)', fontSize: 13, fontWeight: 500,
            background: 'rgba(255,255,255,.08)', border: '1px solid rgba(255,255,255,.16)', color: '#fff',
          }}>Assign</button>
          <button onClick={() => setCheckedIds(new Set())} style={{
            padding: '5px 10px', borderRadius: 'var(--r-s)', fontSize: 13, fontWeight: 500,
            background: 'rgba(255,255,255,.08)', border: '1px solid rgba(255,255,255,.16)', color: '#fff',
          }}>Clear</button>
        </div>
      )}
    </div>
  )
}

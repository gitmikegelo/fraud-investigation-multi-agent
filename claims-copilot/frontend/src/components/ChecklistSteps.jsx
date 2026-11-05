import { useState } from 'react'

export const STEP_NAMES = [
  'Initial Review',
  'Shipping Documents',
  'Transit & Coverage Period',
  'Document AI Review',
  'Survey & Surveyor',
  'ICC Coverage & Exclusions',
  'Final Determination',
]

export const RESULT = {
  pass:         { label: 'Passed', tone: 'ok',   color: 'var(--low)',  bg: 'var(--low-soft)',  bar: 'var(--low-bar)' },
  needs_review: { label: 'Review', tone: 'med',  color: 'var(--med)',  bg: 'var(--med-soft)',  bar: 'var(--med-bar)' },
  fail:         { label: 'Failed', tone: 'high', color: 'var(--high)', bg: 'var(--high-soft)', bar: 'var(--high)' },
}

export const isDone = (status) => status in RESULT

export function countSteps(steps = []) {
  return {
    passed: steps.filter(s => s.status === 'pass').length,
    review: steps.filter(s => s.status === 'needs_review').length,
    failed: steps.filter(s => s.status === 'fail').length,
  }
}

const SEVERITY = /^(BLOCK|FLAG|CRITICAL|WARNING)\b/

function headline(step) {
  const f = step.findings || []
  if (step.status === 'pass') return f.find(x => !SEVERITY.test(x)) || f[0] || ''
  return f.find(x => SEVERITY.test(x)) || f[0] || step.description || ''
}

const DETAIL_LABELS = {
  bl_weight_kg: ['B/L declared weight', v => `${v.toLocaleString()} kg`],
  vgm_gross_kg: ['VGM gross', v => `${v.toLocaleString()} kg`],
  tare_kg: ['Container tare', v => `${v.toLocaleString()} kg`],
  vgm_cargo_kg: ['VGM cargo weight', v => `${v.toLocaleString()} kg`],
  vgm_implied_quantity: ['Quantity the weight supports', v => `~${v.toLocaleString()} m²`],
  risk_score: ['Risk score', v => String(v)],
}

function evidenceRows(step) {
  const d = step.details || {}
  return Object.entries(DETAIL_LABELS)
    .filter(([k]) => typeof d[k] === 'number')
    .map(([k, [label, fmt]]) => [label, fmt(d[k])])
}

// Per-side colours so the spinner's transparent top never conflicts with a shorthand
export const ringColors = (side, top = side) => ({
  borderTopColor: top, borderRightColor: side, borderBottomColor: side, borderLeftColor: side,
})

function StepIcon({ status }) {
  const r = RESULT[status]
  const running = status === 'running'
  const side = r ? 'transparent' : running ? 'var(--accent)' : 'var(--line)'
  return (
    <div style={{
      width: 22, height: 22, borderRadius: '50%', display: 'grid', placeItems: 'center', marginTop: 1,
      borderWidth: 1.5, borderStyle: 'solid',
      ...ringColors(side, running ? 'transparent' : side),
      background: r ? r.bg : 'transparent',
      animation: running ? 'spin .8s linear infinite' : 'none',
    }}>
      {r && (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke={r.color} strokeWidth="2.4" strokeLinecap="round">
          {status === 'pass' && <polyline points="2.5,6.2 4.8,8.5 9.5,3.5" />}
          {status === 'fail' && <><line x1="3" y1="3" x2="9" y2="9" /><line x1="9" y1="3" x2="3" y2="9" /></>}
          {status === 'needs_review' && <><line x1="6" y1="2.5" x2="6" y2="6.7" /><circle cx="6" cy="9.3" r=".8" fill={r.color} stroke="none" /></>}
        </svg>
      )}
    </div>
  )
}

export function MiniBar({ steps }) {
  return (
    <div aria-hidden="true" style={{ display: 'flex', gap: 3, width: 120 }}>
      {steps.map((s, i) => (
        <i key={i} style={{ flex: 1, height: 5, borderRadius: 3, background: RESULT[s.status]?.bar || 'var(--line-2)' }} />
      ))}
    </div>
  )
}

export default function ChecklistSteps({ steps, onAsk }) {
  const [expanded, setExpanded] = useState(null)

  return (
    <ol style={{ listStyle: 'none' }}>
      {steps.map((step, i) => {
        const r = RESULT[step.status]
        const running = step.status === 'running'
        const expandable = !!r && (step.findings || []).length > 0
        const open = expanded === i && expandable
        const summary = headline(step)
        const rows = evidenceRows(step)

        return (
          <li key={step.step_number ?? i} style={{ borderBottom: i < steps.length - 1 ? '1px solid var(--line-2)' : 'none' }}>
            <button
              type="button"
              onClick={() => expandable && setExpanded(open ? null : i)}
              aria-expanded={expandable ? open : undefined}
              style={{
                display: 'grid', gridTemplateColumns: '24px 1fr auto 16px', gap: 12,
                padding: '13px 20px', alignItems: 'start', width: '100%', textAlign: 'left',
                cursor: expandable ? 'pointer' : 'default',
              }}
            >
              <StepIcon status={step.status} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: r || running ? 600 : 500, color: r || running ? 'var(--ink)' : 'var(--muted)' }}>
                  {step.step_name}
                </div>
                {running && <div className="skel" />}
                {r && summary && (
                  <p style={{ color: 'var(--muted)', fontSize: 13, marginTop: 2, maxWidth: '70ch' }}>{summary}</p>
                )}
              </div>
              <span style={{ fontSize: 12.5, fontWeight: 500, paddingTop: 2, color: r ? r.color : 'var(--accent-ink)' }}>
                {r ? r.label : running ? 'Checking…' : ''}
              </span>
              {expandable ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
                  style={{ color: 'var(--muted)', marginTop: 3, transition: 'transform .2s', transform: open ? 'rotate(180deg)' : 'none' }}>
                  <path d="M6 9l6 6 6-6" />
                </svg>
              ) : <span />}
            </button>

            {open && (
              <div style={{ padding: '0 20px 16px 56px' }}>
                <div style={{ fontSize: 13, background: '#FAF9FC', border: '1px solid var(--line-2)', borderRadius: 'var(--r-m)', padding: '12px 14px' }}>
                  {rows.length > 0 && (
                    <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 18px', marginBottom: 10 }}>
                      {rows.map(([label, value]) => (
                        <div key={label} style={{ display: 'contents' }}>
                          <dt style={{ color: 'var(--muted)' }}>{label}</dt>
                          <dd style={{ color: 'var(--ink-2)', fontWeight: 500 }}>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  <ul style={{ listStyle: 'disc', paddingLeft: 18, color: 'var(--ink-2)', display: 'grid', gap: 4 }}>
                    {step.findings.map((f, k) => <li key={k}>{f}</li>)}
                  </ul>
                </div>
                {onAsk && (
                  <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                    <button type="button" onClick={() => onAsk(`Tell me about ${step.step_name}`)}
                      style={{ border: '1px solid var(--accent-line)', background: 'var(--accent-soft)', color: 'var(--accent-ink)', padding: '5px 10px', borderRadius: 'var(--r-s)', fontSize: 13 }}>
                      Ask Copilot
                    </button>
                  </div>
                )}
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}

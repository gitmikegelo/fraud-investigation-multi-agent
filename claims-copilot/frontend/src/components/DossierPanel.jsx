import { useState, useRef, useCallback, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import html2pdf from 'html2pdf.js'
import { Pill } from '../App'

export const REQUIRED_CHECKS = [
  'Documents reconciled', 'Value vs market', 'Photo integrity',
  'Claim frequency', 'Coverage basis', 'Surveyor independence',
]

const plain = (s = '') => s.replace(/\*\*|\*|`/g, '').trim()

function section(md, name) {
  const m = md.match(new RegExp(`^##\\s+${name}[^\\n]*\\n([\\s\\S]*?)(?=^##\\s|(?![\\s\\S]))`, 'mi'))
  return m ? m[1] : ''
}

function field(md, name) {
  const m = md.match(new RegExp(`^\\*\\*${name}\\*\\*:\\s*(.+)$`, 'mi'))
  return m ? plain(m[1]) : ''
}

function parseDossier(md) {
  const exec = section(md, 'EXECUTIVE SUMMARY')
  const bottom = plain(exec.match(/\*\*Bottom line\*\*:\s*(.+)/i)?.[1] || '')
  const recs = section(md, 'RECOMMENDATIONS')
  const decisionText = (bottom || recs.split('\n').find(l => /^\s*1\./.test(l)) || '').toLowerCase()

  const recommendation = /declin|deny|reject/.test(decisionText) ? 'decline'
    : /approve|pay/.test(decisionText) ? 'approve' : 'investigate'

  const hypothesis = field(md, 'Hypothesis')
  const headline = (hypothesis.split(/\s+—\s+/)[0] || field(md, 'Case Type')).replace(/^./, c => c.toUpperCase())
  const summary = bottom || plain(exec.split('\n\n').find(p => p.trim()) || '')

  const weightOf = (sev) => /critical/i.test(sev) ? 'strong' : /mitigat|low/i.test(sev) ? 'mitigating' : 'moderate'
  const findings = section(md, 'EVIDENCE LEDGER').split('\n')
    .map(l => l.split('|').map(c => c.trim()))
    .filter(c => c.length >= 6 && /^\d+$/.test(c[1]))
    .map(c => {
      const [title, ...rest] = plain(c[2]).split(/\s+—\s+/)
      return { title, detail: rest.join(' — '), weight: weightOf(c[3]), source: plain(c[4]) }
    })
    .sort((a, b) => ['strong', 'moderate', 'mitigating'].indexOf(a.weight) - ['strong', 'moderate', 'mitigating'].indexOf(b.weight))

  const actions = recs.split('\n').filter(l => /^\s*\d+\.\s+/.test(l)).map(l => plain(l.replace(/^\s*\d+\.\s+/, '')))

  return { recommendation, headline, summary, findings, actions }
}

const REC_PILL = {
  decline: ['high', 'Recommendation: decline and refer for investigation'],
  approve: ['ok', 'Recommendation: approve'],
  investigate: ['med', 'Recommendation: refer for investigation'],
}
const WEIGHT = { strong: ['high', 'Strong'], moderate: ['med', 'Moderate'], mitigating: ['ok', 'Mitigating'] }
const ACTION = {
  decline: { verb: 'Decline', done: 'Declined', needsNote: true },
  approve: { verb: 'Approve', done: 'Approved', needsNote: false },
  siu: { verb: 'Refer for investigation', done: 'Referred for investigation', needsNote: true },
  survey: { verb: 'Request survey', done: 'Independent survey requested', needsNote: false },
}

const panel = { background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-l)', overflow: 'hidden' }
const btn = { width: '100%', padding: '8px 14px', borderRadius: 'var(--r-s)', fontWeight: 500, fontSize: 13.5, border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink-2)' }
const primary = { ...btn, border: '1px solid var(--accent)', background: 'var(--grad-primary)', color: '#fff', boxShadow: 'var(--sh-btn)' }

function DecisionDialog({ action, claim, recommendation, initialNote, onClose, onConfirm }) {
  const [note, setNote] = useState(initialNote)
  const [error, setError] = useState(false)
  const noteRef = useRef(null)
  const goRef = useRef(null)
  const a = ACTION[action]
  const amount = `US$${(claim.claim_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

  useEffect(() => {
    const prev = document.activeElement
    ;(a.needsNote ? noteRef : goRef).current?.focus()
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => { window.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [onClose, a.needsNote])

  const body = action === 'approve'
    ? `${recommendation === 'approve' ? 'Copilot recommends approval.' : 'Copilot recommends declining this claim.'} Approving will release payment of ${amount}.`
    : action === 'survey'
      ? 'Copilot will draft the instruction to an insurer-appointed panel surveyor for you to review before it is sent.'
      : 'Add a note for the claim file. The investigations team will see it with the dossier.'

  const confirm = () => {
    if (a.needsNote && !note.trim()) { setError(true); noteRef.current?.focus(); return }
    onConfirm(action, note)
  }

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(22,21,29,.32)', display: 'grid', placeItems: 'center', zIndex: 50, backdropFilter: 'blur(2px)' }}>
      <div onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="dlg-title"
        style={{ background: '#fff', borderRadius: 'var(--r-dialog)', width: 'min(440px, 92vw)', padding: 22, boxShadow: 'var(--sh-dialog)' }}>
        <h2 id="dlg-title" style={{ fontSize: 17, fontWeight: 600 }}>{a.verb} — {claim.case_id}?</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13.5, margin: '6px 0 14px' }}>{body}</p>
        {action !== 'survey' && (
          <textarea ref={noteRef} value={note} onChange={e => { setNote(e.target.value); setError(false) }}
            placeholder={error ? 'A note is required for this decision' : 'Note for the claim file'}
            style={{ width: '100%', minHeight: 74, resize: 'vertical', border: `1px solid ${error ? 'var(--high)' : 'var(--line)'}`, outline: error ? '2px solid var(--high)' : undefined, outlineOffset: -1, borderRadius: 'var(--r-s)', padding: '9px 11px', fontSize: 13, background: 'var(--canvas)', marginBottom: 10 }} />
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button type="button" onClick={onClose} style={{ ...btn, width: 'auto' }}>Cancel</button>
          <button type="button" ref={goRef} onClick={confirm} style={{ ...primary, width: 'auto' }}>{a.verb}</button>
        </div>
      </div>
    </div>
  )
}

export default function DossierPanel({ claim, dossierMarkdown, investigationDone, decision, onDecision, onGoToInvestigation }) {
  const [serverDossier, setServerDossier] = useState(null)
  const [note, setNote] = useState('')
  const [dialog, setDialog] = useState(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const pdfRef = useRef(null)

  useEffect(() => {
    if (dossierMarkdown || !claim?.case_id) return
    fetch(`/api/claims/${claim.case_id}`)
      .then(r => r.json())
      .then(d => { if (d.dossier) setServerDossier(d.dossier) })
      .catch(() => {})
  }, [claim?.case_id, dossierMarkdown])

  const dossier = dossierMarkdown || serverDossier

  const exportPdf = useCallback(async () => {
    if (!pdfRef.current) return
    setPdfBusy(true)
    try {
      await html2pdf().set({
        margin: [0.5, 0.6, 0.5, 0.6],
        filename: `marine_claim_dossier_${claim.case_id}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['css', 'legacy'] },
      }).from(pdfRef.current).save()
    } finally { setPdfBusy(false) }
  }, [claim?.case_id])

  if (!dossier) {
    return (
      <div style={{ ...panel, padding: '40px 38px', borderTop: '3px solid var(--accent)', maxWidth: 720 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600 }}>No dossier yet</h2>
        <p style={{ color: 'var(--ink-2)', fontSize: 14, margin: '8px 0 18px', maxWidth: '60ch' }}>
          The case writer drafts the dossier once its six required checks are met. Run the investigation to start.
        </p>
        <button type="button" onClick={onGoToInvestigation} style={{ ...primary, width: 'auto' }}>Go to investigation</button>
      </div>
    )
  }

  const d = parseDossier(dossier)
  const [recTone, recLabel] = REC_PILL[d.recommendation]
  const primaryAction = d.recommendation === 'approve' ? 'approve' : 'decline'
  const ghostAction = primaryAction === 'approve' ? 'decline' : 'approve'
  const checksMet = investigationDone || /Evidence Sufficient/i.test(dossier)

  return (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) var(--aside-w)', gap: 18, alignItems: 'start' }}>
        <article style={{ ...panel, borderTop: '3px solid var(--accent)', padding: '30px 38px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Pill tone={recTone}>{recLabel}</Pill>
            <button type="button" onClick={exportPdf} disabled={pdfBusy} style={{ ...btn, width: 'auto', marginLeft: 'auto', fontSize: 13, padding: '6px 12px' }}>
              {pdfBusy ? 'Exporting…' : 'Export PDF'}
            </button>
          </div>
          {d.headline && <h2 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-.015em', marginTop: 14, maxWidth: '40ch' }}>{d.headline}</h2>}
          {d.summary && <p style={{ fontSize: 15, color: 'var(--ink-2)', margin: '10px 0 22px', maxWidth: '66ch', lineHeight: 1.55 }}>{d.summary}</p>}

          {d.findings.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '22px 0 8px' }}>Findings</h3>
              {d.findings.map((f, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '22px 1fr auto', gap: 12, padding: '12px 0', borderTop: '1px solid var(--line-2)', fontSize: 13.5, alignItems: 'start' }}>
                  <span style={{ color: 'var(--muted)' }}>{i + 1}</span>
                  <div>
                    <b style={{ fontWeight: 500 }}>{f.title}</b>
                    {f.detail && <p style={{ color: 'var(--muted)', marginTop: 2, fontSize: 13 }}>{f.detail}</p>}
                    {f.source && <p style={{ marginTop: 6, fontSize: 12, color: 'var(--accent-ink)', textDecoration: 'underline', textDecorationColor: 'var(--accent-line)', textUnderlineOffset: 3 }}>{f.source}</p>}
                  </div>
                  <Pill tone={WEIGHT[f.weight][0]}>{WEIGHT[f.weight][1]}</Pill>
                </div>
              ))}
            </>
          )}

          {d.actions.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, fontWeight: 600, margin: '22px 0 8px' }}>Recommended actions</h3>
              <ol style={{ paddingLeft: 20, display: 'grid', gap: 6, fontSize: 13.5, color: 'var(--ink-2)' }}>
                {d.actions.map((a, i) => <li key={i}>{a}</li>)}
              </ol>
            </>
          )}

          <details style={{ marginTop: 24 }}>
            <summary style={{ cursor: 'pointer', fontSize: 13, color: 'var(--muted)', fontWeight: 500 }}>Full investigation report</summary>
            <div className="dossier-md" style={{ fontSize: 13, lineHeight: 1.7, marginTop: 12 }}>
              <Markdown remarkPlugins={[remarkGfm]}>{dossier}</Markdown>
            </div>
          </details>
        </article>

        <aside style={{ position: 'sticky', top: 76, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ ...panel, padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
              <svg width="56" height="56" viewBox="0 0 36 36" aria-hidden="true">
                <defs><linearGradient id="ringGrad" x1="0" x2="1"><stop offset="0" stopColor="#C77DFF" /><stop offset="1" stopColor="#7500C0" /></linearGradient></defs>
                <circle cx="18" cy="18" r="15" fill="none" stroke="var(--line-2)" strokeWidth="3.5" />
                <circle cx="18" cy="18" r="15" fill="none" stroke="url(#ringGrad)" strokeWidth="3.5" strokeLinecap="round"
                  strokeDasharray={`${checksMet ? 94.2 : 0} 94.2`} transform="rotate(-90 18 18)" />
              </svg>
              <div>
                <b style={{ fontSize: 18 }}>{checksMet ? REQUIRED_CHECKS.length : 0} of {REQUIRED_CHECKS.length}</b>
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>required checks met</div>
              </div>
            </div>
            <ul style={{ listStyle: 'none' }}>
              {REQUIRED_CHECKS.map((c, i) => (
                <li key={c} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', fontSize: 13, borderBottom: i < REQUIRED_CHECKS.length - 1 ? '1px solid var(--line-2)' : 'none' }}>
                  {c}<span style={{ fontWeight: 500, color: checksMet ? 'var(--low)' : 'var(--med)' }}>{checksMet ? 'Met' : 'Open'}</span>
                </li>
              ))}
            </ul>
          </div>

          <div style={{ ...panel, padding: 18 }}>
            <h3 style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 10 }}>Your decision</h3>
            {decision ? (
              <p style={{ fontSize: 13.5, color: 'var(--ink-2)' }}><b>{ACTION[decision].done}</b> — recorded on the claim file.</p>
            ) : (
              <>
                <textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Note for the claim file" aria-label="Note for the claim file"
                  style={{ width: '100%', minHeight: 74, resize: 'vertical', border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: '9px 11px', fontSize: 13, background: 'var(--canvas)', marginBottom: 4 }} />
                <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>Required for declines and referrals.</p>
                <div style={{ display: 'grid', gap: 8 }}>
                  <button type="button" onClick={() => setDialog(primaryAction)} style={primary}>{ACTION[primaryAction].verb} claim</button>
                  <button type="button" onClick={() => setDialog('survey')} style={btn}>Request independent survey first</button>
                  <button type="button" onClick={() => setDialog(ghostAction)} style={{ ...btn, border: '1px solid transparent', background: 'transparent' }}>
                    {ACTION[ghostAction].verb} anyway
                  </button>
                </div>
              </>
            )}
          </div>
        </aside>
      </div>

      <div style={{ position: 'absolute', left: '-9999px', top: 0 }}>
        <div ref={pdfRef} className="dossier-md" style={{ fontFamily: 'var(--font)', color: '#1e293b', background: '#fff', padding: '0.4in', fontSize: 11, lineHeight: 1.6, width: '7.2in' }}>
          <Markdown remarkPlugins={[remarkGfm]}>{dossier}</Markdown>
        </div>
      </div>

      {dialog && (
        <DecisionDialog
          action={dialog}
          claim={claim}
          recommendation={d.recommendation}
          initialNote={note}
          onClose={() => setDialog(null)}
          onConfirm={(action) => { setDialog(null); onDecision(action) }}
        />
      )}
    </>
  )
}

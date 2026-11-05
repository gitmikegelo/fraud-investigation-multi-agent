import { useEffect, useRef } from 'react'
import ChecklistSteps, { STEP_NAMES, countSteps, isDone } from './ChecklistSteps'

const PENDING = STEP_NAMES.map((name, i) => ({ step_number: i + 1, step_name: name, status: 'pending' }))

const panel = { background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-l)', overflow: 'hidden' }
const panelHead = { display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid var(--line)' }
const primaryBtn = {
  padding: '8px 14px', borderRadius: 'var(--r-s)', fontWeight: 500, fontSize: 13.5, whiteSpace: 'nowrap',
  background: 'var(--grad-primary)', color: '#fff', border: '1px solid var(--accent)', boxShadow: 'var(--sh-btn)',
}

export default function ChecklistPanel({ claim, chat, onGoToCopilot }) {
  const { checklistState, checklistRunning, isConnected, runChecklist } = chat
  const startedFor = useRef(null)

  useEffect(() => {
    if (!isConnected || !claim?.case_id || checklistState || checklistRunning) return
    if (startedFor.current === claim.case_id) return
    startedFor.current = claim.case_id
    runChecklist()
  }, [isConnected, claim?.case_id, checklistState, checklistRunning, runChecklist])

  const steps = checklistState?.steps?.length ? checklistState.steps : PENDING
  const complete = !!checklistState?.summary
  const doneCount = steps.filter(s => isDone(s.status)).length
  const current = Math.min(doneCount + (complete ? 0 : 1), steps.length)
  const { passed, review, failed } = countSteps(steps)
  const m = claim?.key_metrics || {}

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) var(--chat-w)', gap: 18, alignItems: 'start' }}>
      <div style={panel}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600, flex: 1 }}>Examiner checklist</h2>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>Step {current} of {steps.length}</span>
          <div style={{ width: 120, height: 4, background: 'var(--line-2)', borderRadius: 2, overflow: 'hidden' }}>
            <i style={{
              display: 'block', height: '100%', transition: 'width .5s ease',
              background: 'linear-gradient(90deg, var(--accent-glow), var(--accent))',
              width: `${(doneCount / steps.length) * 100}%`,
            }} />
          </div>
        </div>

        <ChecklistSteps steps={steps} />

        {!complete && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 20px', borderTop: '1px solid var(--line)', background: '#FAF9FC' }}>
            <span style={{ fontSize: 13, color: 'var(--muted)', marginRight: 'auto' }}>
              {isConnected
                ? "Runs in the background. You can leave this page — we'll notify you when it's done."
                : 'Connecting to the claims service…'}
            </span>
          </div>
        )}

        {complete && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px', background: 'var(--accent-soft)', borderTop: '1px solid var(--accent-line)' }}>
            <p style={{ marginRight: 'auto', fontSize: 13.5, color: 'var(--accent-ink)' }}>
              <b>Checklist finished.</b> {passed} passed, {review} need review, {failed} failed.
            </p>
            <button type="button" onClick={onGoToCopilot} style={primaryBtn}>See results</button>
          </div>
        )}
      </div>

      <div style={{ ...panel, position: 'sticky', top: 76 }}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600, flex: 1 }}>Copilot</h2>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>Watching this run</span>
        </div>
        <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13.5 }}>
          <div style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ width: 18, height: 18, borderRadius: 5, background: 'var(--grad-brand)' }} />
            Copilot
          </div>
          <p style={{ color: 'var(--ink-2)' }}>
            {complete
              ? `All seven checks are done: ${passed} passed, ${review} need review, ${failed} failed. Open the results to ask about any of them.`
              : 'Checking the claim against the bill of lading, VGM records, open cover, survey report and document images. Results fill in on the left.'}
          </p>
          <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-m)', padding: 12, fontSize: 13 }}>
            <b style={{ fontWeight: 600 }}>{complete ? 'Claim at a glance' : 'While this runs'}</b>
            {[
              ['Claimed', `US$${(claim?.claim_amount || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`],
              ['Shipment', m.shipment],
              ['B/L', m.bl_number],
              ['Surveyor', claim?.provider_name],
            ].filter(([, v]) => v).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '6px 0', borderTop: '1px solid var(--line-2)', marginTop: 6, color: 'var(--ink-2)' }}>
                <span>{k}</span><span style={{ fontWeight: 500, textAlign: 'right' }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

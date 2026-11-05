import { useState, useRef, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Pill } from '../App'
import ChecklistSteps, { MiniBar, countSteps } from './ChecklistSteps'

const SUGGESTED_PROMPTS = [
  'Why is this claim flagged?',
  'Check the surveyor',
  'Explain the VGM gap',
  'Show prior claims',
]

const panel = { background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-l)', overflow: 'hidden' }
const panelHead = { display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid var(--line)', flexShrink: 0 }
const outlineBtn = { padding: '6px 12px', borderRadius: 'var(--r-s)', fontSize: 13, fontWeight: 500, border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink-2)' }
const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 'var(--r-s)', fontWeight: 500,
  background: 'var(--grad-primary)', color: '#fff', border: '1px solid var(--accent)', boxShadow: 'var(--sh-btn)',
  whiteSpace: 'nowrap', flexShrink: 0,
}
const fbBtn = { fontSize: 12, color: 'var(--muted)', padding: '2px 6px', borderRadius: 4 }

export default function ChatPanel({ chat, onStartInvestigation, onDecision, showToast }) {
  const { messages, isThinking, isConnected, checklistState, sendMessage } = chat
  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const lastRef = useRef(null)
  const listRef = useRef(null)
  const inputRef = useRef(null)

  const steps = checklistState?.steps || []
  const complete = !!checklistState?.summary
  const { passed, review, failed } = countSteps(steps)
  const conversation = messages.filter(m => m.role === 'analyst' || m.role === 'assistant')
  const lastError = [...messages].reverse().find(m => m.role === 'system' && m.text.startsWith('Error'))

  // Long answers: land on the start of the newest message, not its last line
  useEffect(() => {
    const box = listRef.current
    const target = isThinking ? endRef.current : lastRef.current
    if (box && target) box.scrollTo({ top: target.offsetTop - 8, behavior: 'smooth' })
  }, [conversation.length, isThinking])

  const send = (text) => {
    const t = text.trim()
    if (!t || isThinking || !isConnected) return
    sendMessage(t)
    setInput('')
  }

  const ask = (text) => { setInput(text); inputRef.current?.focus() }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) var(--chat-w)', gap: 18, alignItems: 'start' }}>
      <div style={panel}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600 }}>Examiner checklist</h2>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            <MiniBar steps={steps} />
            <Pill tone="ok">{passed} passed</Pill>
            <Pill tone="med">{review} review</Pill>
            <Pill tone="high">{failed} failed</Pill>
          </div>
        </div>

        {steps.length === 0 ? (
          <p style={{ padding: '20px', color: 'var(--muted)', fontSize: 13 }}>The checklist hasn't run yet. Open the Checklist page to start it.</p>
        ) : (
          <ChecklistSteps steps={steps} onAsk={ask} />
        )}

        {complete && review + failed > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px', borderTop: '1px solid var(--accent-line)', background: 'linear-gradient(120deg,#FBF7FF 0%,#F3E9FF 100%)' }}>
            <div style={{ marginRight: 'auto' }}>
              <b style={{ fontWeight: 600, color: 'var(--accent-ink)', fontSize: 13.5 }}>
                {review + failed} checks need evidence the checklist can't gather.
              </b>
              <p style={{ fontSize: 13, color: 'var(--ink-2)', maxWidth: '54ch', marginTop: 2 }}>
                Copilot can trace the claimant, surveyor and forwarder, check the survey history, and draft a dossier. It stops for your review before anything is decided.
              </p>
            </div>
            <button type="button" onClick={onStartInvestigation} style={primaryBtn}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
                <circle cx="11" cy="11" r="6.5" /><path d="M20 20l-4-4" />
              </svg>
              Start investigation
            </button>
          </div>
        )}

        {complete && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '14px 20px', borderTop: '1px solid var(--line)', background: '#FAF9FC' }}>
            <span style={{ fontSize: 13, color: 'var(--muted)', marginRight: 'auto' }}>Ready to decide now?</span>
            <button type="button" onClick={() => onDecision('approve')} style={outlineBtn}>Approve</button>
            <button type="button" onClick={() => onDecision('decline')} style={outlineBtn}>Decline</button>
            <button type="button" onClick={() => onDecision('siu')} style={{ ...outlineBtn, borderColor: '#EFC7CB', background: 'transparent', color: 'var(--high)' }}>Refer to SIU</button>
          </div>
        )}
      </div>

      <div style={{ ...panel, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 56px - 210px)', minHeight: 520, position: 'sticky', top: 76 }}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600, flex: 1 }}>Copilot</h2>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>{isConnected ? 'Answers cite their source' : 'Reconnecting…'}</span>
        </div>

        <div ref={listRef} aria-live="polite" style={{ position: 'relative', flex: 1, overflow: 'auto', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {conversation.length === 0 && !isThinking && (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>Ask about any check, the shipment documents, the surveyor or the claimant's history.</p>
          )}
          {conversation.map((msg, i) => {
            const mine = msg.role === 'analyst'
            return (
              <div key={i} ref={i === conversation.length - 1 ? lastRef : undefined} style={{ maxWidth: '92%', fontSize: 13.5, alignSelf: mine ? 'flex-end' : 'flex-start', scrollMarginTop: 8 }}>
                {!mine && (
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 5, display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span style={{ width: 18, height: 18, borderRadius: 5, background: 'var(--grad-brand)' }} />
                    Copilot
                  </div>
                )}
                {mine ? (
                  <div style={{ padding: '9px 13px', borderRadius: '12px 12px 4px 12px', background: 'var(--grad-user-bubble)', color: '#fff' }}>{msg.text}</div>
                ) : (
                  <div className="chat-md" style={{ color: 'var(--ink-2)' }}>
                    <Markdown remarkPlugins={[remarkGfm]}>{msg.text}</Markdown>
                  </div>
                )}
                {!mine && (
                  <div style={{ display: 'flex', gap: 2, marginTop: 6 }}>
                    <button type="button" style={fbBtn} onClick={() => showToast('Thanks — feedback saved')}>Helpful</button>
                    <button type="button" style={fbBtn} onClick={() => showToast("Thanks — we'll use this to improve")}>Not helpful</button>
                    <button type="button" style={fbBtn} onClick={() => { navigator.clipboard?.writeText(msg.text).catch(() => {}); showToast('Copied') }}>Copy</button>
                  </div>
                )}
              </div>
            )
          })}
          {isThinking && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--accent-soft)', borderRadius: 12 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', animation: 'pulse 1.4s ease-in-out infinite' }} />
              <span style={{ fontSize: 12.5, color: 'var(--accent-ink)' }}>Copilot is checking the file…</span>
            </div>
          )}
          {lastError && !isThinking && (
            <p style={{ fontSize: 12.5, color: 'var(--high)' }}>{lastError.text}</p>
          )}
          <div ref={endRef} />
        </div>

        <div style={{ padding: '0 20px 12px', display: 'flex', gap: 6, flexWrap: 'wrap', flexShrink: 0 }}>
          {SUGGESTED_PROMPTS.map(p => (
            <button type="button" key={p} onClick={() => send(p)} disabled={isThinking || !isConnected}
              style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-pill)', padding: '5px 10px', fontSize: 12.5, color: 'var(--ink-2)', background: 'var(--surface)' }}>
              {p}
            </button>
          ))}
        </div>

        <form onSubmit={e => { e.preventDefault(); send(input) }} style={{ borderTop: '1px solid var(--line)', padding: 12, display: 'flex', gap: 8, flexShrink: 0 }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about this claim…"
            aria-label="Message Copilot"
            style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: '9px 12px', background: 'var(--canvas)', fontSize: 13 }}
          />
          <button type="submit" disabled={!input.trim() || isThinking || !isConnected}
            style={{ ...primaryBtn, padding: '9px 16px', fontSize: 13, opacity: !input.trim() || isThinking || !isConnected ? 0.5 : 1 }}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}

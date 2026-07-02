import { useState, useRef, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import html2pdf from 'html2pdf.js'
import { useCopilotChat } from '../hooks/useCopilotChat'

const PRIORITY_COLORS = {
  HIGH:   '#ef4444',
  MEDIUM: '#f59e0b',
  LOW:    '#6b7280',
}

const COMMON_CHIPS = [
  { label: '▶ Run Full Checklist', action: 'checklist' },
  { label: 'Check Eligibility',    prompt: 'Check eligibility for this claim' },
  { label: 'Workflow Tasks',       prompt: 'What is the current workflow task status?' },
  { label: 'Why Flagged?',         prompt: 'Why was this claim flagged? Explain the risk score.' },
  { label: 'Escalate',             prompt: 'Compile an escalation dossier for this claim' },
]

const TYPE_CHIPS = {
  collision: [
    { label: 'Verify Estimate',  prompt: 'Verify the repair estimate against the vehicle value' },
    { label: 'Shop Risk',        prompt: 'Check the repair shop watchlist status for this claim' },
  ],
  comprehensive: [
    { label: 'Verify Estimate',  prompt: 'Verify the repair estimate against the vehicle value' },
    { label: 'Documents',        prompt: 'Analyze the damage photos and documents for this claim' },
  ],
  theft: [
    { label: 'Match to Policy',  prompt: 'Does this theft claim match the policy coverage and ACV?' },
    { label: 'Claim History',    prompt: 'Show related claims for this insured' },
  ],
  liability: [
    { label: 'Match to Policy',  prompt: 'Does this claim match the policy coverage limits?' },
    { label: 'Claim History',    prompt: 'Check the insured claim history for serial-claim patterns' },
  ],
  medical_payments: [
    { label: 'Injury Review',    prompt: 'Review the injury claim and supporting documents' },
    { label: 'Policy Check',     prompt: 'Get full policy details and any alerts' },
  ],
}

export default function ChatPanel({ caseId, caseType, caseSummary, onBack, onNavigateToDossier, onStartAutoScan }) {
  const { messages, isThinking, isConnected, checklistState, checklistRunning, sendMessage, runChecklist } = useCopilotChat(caseId)
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // DECREE full evaluation runs in the background; the bell surfaces its status.
  // decreeEval: null | { loading } | { report_markdown, cost_*, confidence, ... } | { error }
  const [decreeEval, setDecreeEval] = useState(null)
  const [decreeSeen, setDecreeSeen] = useState(true)   // false once a result is ready but unopened
  const [decreeOpen, setDecreeOpen] = useState(false)  // overlay visibility
  const [decreePdfGenerating, setDecreePdfGenerating] = useState(false)
  const decreeReportRef = useRef(null)

  const downloadDecreePdf = async () => {
    if (!decreeReportRef.current) return
    setDecreePdfGenerating(true)
    try {
      const opt = {
        margin:      [0.5, 0.6, 0.5, 0.6],
        filename:    `decree_evaluation_${caseId || 'claim'}_${new Date().toISOString().slice(0, 10)}.pdf`,
        image:       { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF:       { unit: 'in', format: 'letter', orientation: 'portrait' },
        pagebreak:   { mode: ['avoid-all', 'css', 'legacy'] },
      }
      await html2pdf().set(opt).from(decreeReportRef.current).save()
    } finally {
      setDecreePdfGenerating(false)
    }
  }

  const runDecreeFull = () => {
    // Kick off in the background — do not block the UI.
    setDecreeEval({ loading: true })
    setDecreeSeen(true)
    setDecreeOpen(false)
    ;(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/claims/${caseId}/decree/full`)
        const json = await res.json()
        setDecreeEval(json.error ? { error: json.error } : json)
      } catch {
        setDecreeEval({ error: 'Could not reach the DECREE service.' })
      }
      setDecreeSeen(false)  // ready & unread → light up the bell
    })()
  }

  const decreeBusy = decreeEval?.loading
  const decreeReady = decreeEval && !decreeEval.loading
  const bellAlert = decreeReady && !decreeSeen

  const chips = [...COMMON_CHIPS, ...(TYPE_CHIPS[caseSummary?.claim_type] || [])]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const riskColor = PRIORITY_COLORS[caseSummary?.priority] || '#6b7280'
  const ruleCount = caseSummary?.rules_triggered?.length || 0
  const taskCount = caseSummary?.workflow_tasks?.length || 0

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Case header */}
      <div style={{
        padding: '12px 20px', background: 'var(--c-surface)',
        borderBottom: '1px solid var(--c-border)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={{
            background: 'transparent', border: '1px solid var(--c-border)', borderRadius: 6,
            color: 'var(--c-text-dim)', cursor: 'pointer', padding: '4px 10px', fontSize: 12,
          }}>← Queue</button>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--c-blue)', fontFamily: 'ui-monospace, monospace' }}>
                {caseSummary?.case_id || caseId}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-text)' }}>
                {caseSummary?.subject_name || ''}
              </span>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 10,
                background: 'var(--c-accent-soft)', color: 'var(--c-accent)', fontWeight: 600,
              }}>
                {caseSummary?.claim_type?.replace('_', ' ') || caseType}
              </span>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                fontSize: 11, fontWeight: 700, color: riskColor,
              }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: riskColor }} />
                {caseSummary?.risk_score || 0}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--c-text-dim)', marginTop: 2, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {caseSummary?.employer_name && <span>{caseSummary.employer_name}</span>}
              {caseSummary?.claim_amount > 0 && <span>${caseSummary.claim_amount.toLocaleString()}</span>}
              {caseSummary?.coverage_start && <span>Coverage: {caseSummary.coverage_start} – {caseSummary.coverage_end || 'Active'}</span>}
            </div>
          </div>
          {/* DECREE notification bell — appears once a full evaluation is running or ready */}
          {decreeEval && (
            <button
              onClick={() => { setDecreeOpen(true); setDecreeSeen(true) }}
              title={decreeBusy ? 'DECREE evaluation running…' : 'DECREE full evaluation ready'}
              style={{
                position: 'relative', width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                border: '1px solid var(--c-border)', background: 'transparent',
                color: bellAlert ? 'var(--c-blue)' : 'var(--c-text-dim)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 15, transition: 'all 0.15s',
                animation: decreeBusy ? 'pulse 1.5s ease-in-out infinite' : 'none',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--c-accent-faint)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
            >
              🔔
              {bellAlert && (
                <span style={{
                  position: 'absolute', top: -3, right: -3,
                  minWidth: 15, height: 15, padding: '0 3px', borderRadius: 8,
                  background: '#ef4444', border: '2px solid var(--c-surface)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 9, fontWeight: 700, color: '#fff',
                }}>
                  {decreeEval.error ? '!' : '1'}
                </span>
              )}
            </button>
          )}
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: isConnected ? '#22c55e' : '#ef4444',
          }} />
        </div>

        {/* Alert banner */}
        {(ruleCount > 0 || taskCount > 0) && (
          <div style={{
            marginTop: 8, padding: '6px 12px', borderRadius: 8,
            background: ruleCount > 0 ? 'rgba(239,68,68,0.06)' : 'var(--c-accent-faint)',
            border: `1px solid ${ruleCount > 0 ? 'rgba(239,68,68,0.15)' : 'var(--c-accent-soft)'}`,
            fontSize: 11, color: 'var(--c-text-dim)', display: 'flex', gap: 16,
          }}>
            {ruleCount > 0 && <span>🚩 {ruleCount} rules triggered</span>}
            {taskCount > 0 && <span>📋 {taskCount} workflow tasks</span>}
          </div>
        )}

        {/* Checklist progress bar */}
        {checklistState?.steps && (
          <div style={{ marginTop: 8, display: 'flex', gap: 3 }}>
            {checklistState.steps.map((s, i) => (
              <div key={i} title={`${s.step_name}: ${s.status}`} style={{
                flex: 1, height: 5, borderRadius: 3,
                background: s.status === 'pass' ? '#22c55e' : s.status === 'fail' ? '#ef4444' : s.status === 'needs_review' ? '#f59e0b' : '#e2e8f0',
              }} />
            ))}
          </div>
        )}
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, overflow: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {messages.map((msg, i) => (
          msg.role === 'checklist'
            ? <ChecklistCard key={i} msg={msg} caseId={caseId} onStartAutoScan={onStartAutoScan} onRunDecreeFull={runDecreeFull} decreeBusy={decreeBusy} />
            : <MessageBubble key={i} msg={msg} onNavigateToDossier={onNavigateToDossier} />
        ))}

        {isThinking && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
            background: 'var(--c-accent-faint)', borderRadius: 12, alignSelf: 'flex-start',
          }}>
            <span className="animate-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--c-accent)' }} />
            <span style={{ fontSize: 12, color: 'var(--c-accent)', fontStyle: 'italic' }}>Copilot is thinking…</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Checklist loading overlay */}
      {checklistRunning && (
        <ChecklistLoadingOverlay steps={checklistState?.steps} />
      )}

      {/* Quick action chips */}
      <div style={{
        padding: '8px 20px', borderTop: '1px solid var(--c-border)',
        background: 'var(--c-surface)', flexShrink: 0,
        display: 'flex', gap: 6, flexWrap: 'wrap',
      }}>
        {chips.map(c => (
          <button key={c.label} onClick={() => c.action === 'checklist' ? runChecklist() : sendMessage(c.prompt)} disabled={isThinking || checklistRunning} style={{
            fontSize: 11, padding: '4px 12px', borderRadius: 14,
            border: '1px solid var(--c-border)', background: 'transparent',
            color: 'var(--c-text-dim)', cursor: (isThinking || checklistRunning) ? 'not-allowed' : 'pointer',
            opacity: (isThinking || checklistRunning) ? 0.5 : 1, transition: 'all 0.12s',
          }}
          onMouseEnter={e => { if (!isThinking && !checklistRunning) e.currentTarget.style.borderColor = 'var(--c-accent)' }}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--c-border)'}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Input bar */}
      <div style={{
        padding: '12px 20px', borderTop: '1px solid var(--c-border)',
        background: 'var(--c-surface)', flexShrink: 0,
        display: 'flex', gap: 10, alignItems: 'flex-end',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about this claim…"
          rows={1}
          style={{
            flex: 1, padding: '10px 14px', borderRadius: 10,
            border: '1px solid var(--c-border)', background: 'var(--c-surface2)',
            color: 'var(--c-text)', fontSize: 13, resize: 'none',
            outline: 'none', fontFamily: 'inherit', lineHeight: 1.4,
            minHeight: 40, maxHeight: 120,
          }}
          onFocus={e => e.target.style.borderColor = 'var(--c-accent)'}
          onBlur={e => e.target.style.borderColor = 'var(--c-border)'}
        />
        <button onClick={handleSend} disabled={isThinking || !input.trim()} style={{
          padding: '10px 22px', borderRadius: 'var(--r-btn)', border: 'none',
          background: (isThinking || !input.trim()) ? 'var(--c-accent-soft)' : 'linear-gradient(90deg, #a100ff, #d6298a)',
          color: (isThinking || !input.trim()) ? 'var(--c-accent)' : '#fff',
          fontSize: 12, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
          cursor: (isThinking || !input.trim()) ? 'not-allowed' : 'pointer',
          transition: 'all 0.15s', flexShrink: 0,
        }}>
          Send
        </button>
      </div>

      {/* DECREE full-evaluation overlay — opened from the notification bell */}
      {decreeOpen && decreeEval && (
        <div
          onClick={() => setDecreeOpen(false)}
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, cursor: 'pointer',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'relative', width: 'min(760px, 92vw)', maxHeight: '90vh',
              background: 'var(--c-surface)', borderRadius: 12,
              boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
              overflow: 'hidden', display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Overlay header */}
            <div style={{
              padding: '12px 18px', display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', borderBottom: '1px solid var(--c-border)',
              background: 'linear-gradient(135deg, rgba(41,98,255,0.08) 0%, transparent 100%)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>📊</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--c-text)' }}>
                    Full Damage Evaluation
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--c-text-dim)', fontStyle: 'italic', marginTop: 1 }}>
                    Powered by DECREE<sup>™</sup>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {decreeReady && !decreeEval.error && decreeEval.report_markdown && (
                  <div
                    onClick={downloadDecreePdf}
                    style={{
                      padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: 6,
                      cursor: decreePdfGenerating ? 'default' : 'pointer',
                      background: 'var(--c-blue-soft)', border: '1px solid rgba(41,98,255,0.2)',
                      borderRadius: 8, fontSize: 11, fontWeight: 600,
                      color: 'var(--c-blue)', opacity: decreePdfGenerating ? 0.6 : 1,
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { if (!decreePdfGenerating) e.currentTarget.style.background = 'rgba(41,98,255,0.15)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--c-blue-soft)' }}
                  >
                    {decreePdfGenerating ? '⏳ Generating…' : '⬇ Download PDF'}
                  </div>
                )}
                <div
                  onClick={() => setDecreeOpen(false)}
                  style={{
                    width: 28, height: 28, borderRadius: 8, cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, color: 'var(--c-text-dim)', fontWeight: 700,
                    background: 'rgba(100,116,139,0.1)', transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; e.currentTarget.style.color = '#ef4444' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(100,116,139,0.1)'; e.currentTarget.style.color = 'var(--c-text-dim)' }}
                >
                  ✕
                </div>
              </div>
            </div>

            {/* Overlay body */}
            <div style={{ overflow: 'auto', padding: 20, cursor: 'default' }}>
              {decreeEval.loading ? (
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  justifyContent: 'center', gap: 16, padding: '48px 0',
                }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: '50%',
                    border: '3px solid var(--c-blue-soft)',
                    borderTopColor: 'var(--c-blue)',
                    animation: 'spin 0.8s linear infinite',
                  }} />
                  <div style={{ fontSize: 12, color: 'var(--c-text-dim)', fontWeight: 500 }}>
                    Running full DECREE<sup>™</sup> evaluation…
                  </div>
                </div>
              ) : decreeEval.error ? (
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  gap: 12, padding: '40px 0', textAlign: 'center',
                }}>
                  <span style={{ fontSize: 28 }}>⚠️</span>
                  <div style={{ fontSize: 12, color: 'var(--c-text)', maxWidth: 380 }}>
                    {decreeEval.error}
                  </div>
                  <div
                    onClick={runDecreeFull}
                    style={{
                      padding: '6px 14px', cursor: 'pointer', borderRadius: 8,
                      background: 'var(--c-blue-soft)', border: '1px solid rgba(41,98,255,0.2)',
                      fontSize: 11, fontWeight: 600, color: 'var(--c-blue)',
                    }}
                  >
                    Retry
                  </div>
                </div>
              ) : (
                <div ref={decreeReportRef}>
                  {(decreeEval.cost_low != null && decreeEval.cost_high != null) && (
                    <div style={{
                      display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'baseline',
                      padding: '10px 14px', marginBottom: 16, borderRadius: 8,
                      background: 'var(--c-accent-faint)', border: '1px solid var(--c-border)',
                    }}>
                      <div>
                        <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--c-text-dim)' }}>Estimated cost</div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-text)' }}>
                          ${decreeEval.cost_low.toLocaleString()}–${decreeEval.cost_high.toLocaleString()}
                          {decreeEval.cost_mid != null && (
                            <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--c-text-dim)' }}>
                              {'  (midpoint $'}{decreeEval.cost_mid.toLocaleString()}{')'}
                            </span>
                          )}
                        </div>
                      </div>
                      {decreeEval.confidence != null && (
                        <div>
                          <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--c-text-dim)' }}>Confidence</div>
                          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-text)' }}>
                            {decreeEval.confidence}%
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: 'var(--c-text)', lineHeight: 1.6 }}>
                    <Markdown remarkPlugins={[remarkGfm]}>
                      {decreeEval.report_markdown || '_No report content returned._'}
                    </Markdown>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* CSS animations for the DECREE spinner + notification bell */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.92); }
        }
      `}</style>
    </div>
  )
}


function MessageBubble({ msg, onNavigateToDossier }) {
  const [toolOpen, setToolOpen] = useState(false)

  if (msg.role === 'system') {
    return (
      <div style={{
        fontSize: 11, color: '#64748b', textAlign: 'center',
        padding: '6px 0', fontStyle: 'italic',
      }}>
        {msg.text}
      </div>
    )
  }

  if (msg.role === 'tool') {
    return (
      <div style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
        <button onClick={() => setToolOpen(!toolOpen)} style={{
          fontSize: 11, color: 'var(--c-accent)', background: 'var(--c-accent-faint)',
          border: '1px solid var(--c-accent-soft)', borderRadius: 8,
          padding: '5px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ fontSize: 10 }}>🔧</span>
          {msg.tool}
          <span style={{ fontSize: 9, opacity: 0.6 }}>{toolOpen ? '▲' : '▼'}</span>
        </button>
        {toolOpen && (
          <div style={{
            marginTop: 4, padding: '8px 12px', background: 'var(--c-accent-faint)',
            borderRadius: 8, fontSize: 11, color: 'var(--c-text-dim)',
            fontFamily: 'ui-monospace, monospace', whiteSpace: 'pre-wrap',
          }}>
            {msg.text}
          </div>
        )}
      </div>
    )
  }

  const isAnalyst = msg.role === 'analyst'

  // Detect and strip the [[VIEW_DOSSIER_TAB]] marker from copilot messages
  const DOSSIER_MARKER = '[[VIEW_DOSSIER_TAB]]'
  const hasDossierPrompt = !isAnalyst && typeof msg.text === 'string' && msg.text.includes(DOSSIER_MARKER)
  const displayText = hasDossierPrompt ? msg.text.replace(DOSSIER_MARKER, '').trimEnd() : msg.text

  return (
    <div style={{ alignSelf: isAnalyst ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
      <div style={{
        fontSize: 10, fontWeight: 600, marginBottom: 3,
        color: isAnalyst ? 'var(--c-accent)' : 'var(--c-text-dim)',
        textAlign: isAnalyst ? 'right' : 'left',
      }}>
        {isAnalyst ? 'You' : 'Copilot'}
      </div>
      <div style={{
        padding: '10px 14px', borderRadius: 12,
        background: isAnalyst ? 'var(--c-accent-soft)' : 'var(--c-surface2)',
        border: isAnalyst ? '1px solid var(--c-accent-soft)' : '1px solid var(--c-border)',
        color: 'var(--c-text)', fontSize: 13, lineHeight: 1.55,
      }}>
        {isAnalyst ? (
          displayText
        ) : (
          <div className="chat-markdown">
            <Markdown remarkPlugins={[remarkGfm]}>{displayText}</Markdown>
          </div>
        )}
      </div>
      {hasDossierPrompt && onNavigateToDossier && (
        <button
          onClick={onNavigateToDossier}
          style={{
            marginTop: 8, display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 12, fontWeight: 600, padding: '7px 16px', borderRadius: 'var(--r-btn)',
            background: 'transparent', border: '1px solid var(--c-accent)',
            color: 'var(--c-accent)', cursor: 'pointer', transition: 'all 0.15s', width: '100%',
            justifyContent: 'center', textTransform: 'uppercase', letterSpacing: '0.03em',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--c-accent-soft)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
        >
          <svg width="13" height="13" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 2a1.5 1.5 0 011.5-1.5H10L13 4v8.5A1.5 1.5 0 0111.5 14h-7A1.5 1.5 0 013 12.5V2z"/>
            <path d="M9.5.5V4H13"/>
          </svg>
          View Full Dossier →
        </button>
      )}
    </div>
  )
}


const STATUS_CONFIG = {
  pass:         { icon: '✓', color: '#22c55e', bg: 'rgba(34,197,94,0.10)',  border: 'rgba(34,197,94,0.25)',  label: 'Passed' },
  fail:         { icon: '✕', color: '#ef4444', bg: 'rgba(239,68,68,0.10)',  border: 'rgba(239,68,68,0.25)',  label: 'Failed' },
  needs_review: { icon: '!', color: '#f59e0b', bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.25)', label: 'Review' },
  running:      { icon: '◌', color: '#a100ff', bg: 'rgba(161,0,255,0.10)', border: 'rgba(161,0,255,0.25)', label: 'Running' },
  pending:      { icon: '○', color: '#64748b', bg: 'rgba(100,116,139,0.06)',border: 'rgba(100,116,139,0.12)',label: 'Pending' },
  error:        { icon: '⚠', color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)',   label: 'Error' },
}

const CHECKLIST_QUIPS = [
  { icon: '🔍', text: 'Verifying the claim paperwork is not written in crayon…' },
  { icon: '🚗', text: 'Checking if the car actually exists and isn\'t a LEGO set…' },
  { icon: '📸', text: 'Counting pixels in damage photos. Every dent tells a story.' },
  { icon: '🔮', text: 'Consulting the actuarial oracle for cosmic guidance…' },
  { icon: '📋', text: 'Cross-referencing 47 databases. The databases are judging us.' },
  { icon: '🕵️', text: 'Looking for red flags. And yellow ones. And slightly suspicious beige ones.' },
  { icon: '💸', text: 'Calculating if the repair costs more than the car is worth…' },
  { icon: '🧾', text: 'Reading every receipt ever submitted in the history of insurance.' },
  { icon: '🤖', text: 'AI is thinking very hard. Please offer it encouragement.' },
  { icon: '📊', text: 'Running risk models. The math is being very dramatic about it.' },
  { icon: '🗂️', text: 'Filing things alphabetically. "Suspicious" comes after "Suspicious-ish".' },
  { icon: '⚖️', text: 'Weighing the evidence. The scale tips slightly toward paperwork.' },
  { icon: '🏎️', text: 'Checking if the vehicle speed matches the excuse given…' },
  { icon: '📡', text: 'Pinging satellite data. The satellite is also confused.' },
  { icon: '🔦', text: 'Shining a light into the dark corners of this claim…' },
]

function ChecklistLoadingOverlay({ steps }) {
  const [quipIndex, setQuipIndex] = useState(0)
  const [fade, setFade] = useState(true)
  const [dots, setDots] = useState(0)

  const completedCount = steps ? steps.filter(s => !['pending', 'running'].includes(s.status)).length : 0
  const totalSteps = steps ? steps.length : 7
  const pct = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0
  const runningStep = steps ? steps.find(s => s.status === 'running') : null

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(false)
      setTimeout(() => {
        setQuipIndex(i => (i + 1) % CHECKLIST_QUIPS.length)
        setFade(true)
      }, 300)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => setDots(d => (d + 1) % 4), 400)
    return () => clearInterval(interval)
  }, [])

  const quip = CHECKLIST_QUIPS[quipIndex]
  const circumference = 2 * Math.PI * 36
  const strokeDash = circumference - (pct / 100) * circumference

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(10,10,20,0.72)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 800,
    }}>
      <div style={{
        background: 'var(--c-surface)',
        border: '1px solid var(--c-border)',
        borderRadius: 20,
        padding: '36px 44px',
        maxWidth: 440,
        width: '90vw',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
        boxShadow: '0 32px 80px rgba(0,0,0,0.45), 0 0 0 1px rgba(161,0,255,0.08)',
      }}>

        {/* Animated ring */}
        <div style={{ position: 'relative', width: 96, height: 96 }}>
          <svg width="96" height="96" viewBox="0 0 96 96" style={{ transform: 'rotate(-90deg)' }}>
            {/* Track */}
            <circle cx="48" cy="48" r="36" fill="none" stroke="var(--c-border)" strokeWidth="5" />
            {/* Progress arc */}
            <circle
              cx="48" cy="48" r="36" fill="none"
              stroke="url(#clGrad)" strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDash}
              style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.4,0,0.2,1)' }}
            />
            <defs>
              <linearGradient id="clGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#a100ff" />
                <stop offset="100%" stopColor="#2962ff" />
              </linearGradient>
            </defs>
          </svg>
          {/* Center icon */}
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 2,
          }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--c-text)', letterSpacing: '-0.5px' }}>
              {pct}%
            </span>
            <span style={{ fontSize: 9, color: 'var(--c-text-dim)', fontWeight: 600 }}>
              {completedCount}/{totalSteps}
            </span>
          </div>
        </div>

        {/* Title */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-text)', letterSpacing: '-0.2px' }}>
            Running 7-Step Examiner Checklist
          </div>
          <div style={{ fontSize: 12, color: 'var(--c-text-dim)', marginTop: 4 }}>
            {runningStep
              ? <>Analysing: <span style={{ color: 'var(--c-accent)', fontWeight: 600 }}>{runningStep.step_name}</span></>
              : 'Preparing examination…'}
            {'.'.repeat(dots)}
          </div>
        </div>

        {/* Step pills */}
        {steps && (
          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 340 }}>
            {steps.map((s, i) => {
              const isRunning = s.status === 'running'
              const isDone = !['pending', 'running'].includes(s.status)
              const color = s.status === 'pass' ? '#22c55e'
                : s.status === 'fail' ? '#ef4444'
                : s.status === 'needs_review' ? '#f59e0b'
                : isRunning ? '#a100ff'
                : 'var(--c-border)'
              return (
                <div key={i} title={s.step_name} style={{
                  height: 6, width: isDone || isRunning ? 28 : 18,
                  borderRadius: 3,
                  background: color,
                  opacity: s.status === 'pending' ? 0.25 : 1,
                  transition: 'all 0.4s cubic-bezier(0.4,0,0.2,1)',
                  animation: isRunning ? 'clPulse 1.2s ease-in-out infinite' : 'none',
                }} />
              )
            })}
          </div>
        )}

        {/* Rotating quip */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(161,0,255,0.06) 0%, rgba(41,98,255,0.05) 100%)',
          border: '1px solid var(--c-border)',
          borderRadius: 12,
          padding: '14px 18px',
          width: '100%',
          minHeight: 60,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          transition: 'opacity 0.3s ease',
          opacity: fade ? 1 : 0,
        }}>
          <span style={{ fontSize: 22, flexShrink: 0 }}>{quip.icon}</span>
          <span style={{ fontSize: 12, color: 'var(--c-text-dim)', lineHeight: 1.5, fontStyle: 'italic' }}>
            {quip.text}
          </span>
        </div>

        <div style={{ fontSize: 10, color: 'var(--c-text-dim)', opacity: 0.5, letterSpacing: '0.5px' }}>
          YOUR CLAIM IS IN GOOD HANDS
        </div>
      </div>

      <style>{`
        @keyframes clPulse {
          0%, 100% { opacity: 1; transform: scaleX(1); }
          50% { opacity: 0.5; transform: scaleX(0.85); }
        }
      `}</style>
    </div>
  )
}

function ChecklistCard({ msg, onStartAutoScan, onRunDecreeFull, decreeBusy }) {
  const [expandedStep, setExpandedStep] = useState(null)
  const [docImageUrl, setDocImageUrl] = useState(null)
  const { steps, summary, complete } = msg

  const passCount = steps.filter(s => s.status === 'pass').length
  const totalDone = steps.filter(s => !['pending', 'running'].includes(s.status)).length

  return (
    <div style={{
      alignSelf: 'flex-start', width: '100%', maxWidth: '92%',
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, marginBottom: 3,
        color: '#64748b', textAlign: 'left',
      }}>
        Copilot
      </div>
      <div style={{
        borderRadius: 14, overflow: 'hidden',
        border: '1px solid var(--c-border)',
        background: 'var(--c-surface)',
      }}>
        {/* Card header */}
        <div style={{
          padding: '14px 18px 12px',
          background: 'linear-gradient(135deg, rgba(161,0,255,0.07) 0%, rgba(41,98,255,0.06) 100%)',
          borderBottom: '1px solid var(--c-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'var(--c-accent-soft)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14,
            }}>
              {complete ? '📋' : '⏳'}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--c-text)' }}>
                7-Step Examiner Checklist
              </div>
              <div style={{ fontSize: 11, color: 'var(--c-text-dim)', marginTop: 1 }}>
                {complete
                  ? `Complete — ${passCount}/7 passed`
                  : `Running step ${totalDone + 1} of 7…`}
              </div>
            </div>
          </div>
          {/* Mini progress dots */}
          <div style={{ display: 'flex', gap: 4 }}>
            {steps.map((s, i) => {
              const cfg = STATUS_CONFIG[s.status] || STATUS_CONFIG.pending
              return (
                <div key={i} title={`${s.step_name}: ${cfg.label}`} style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: cfg.color,
                  opacity: s.status === 'pending' ? 0.3 : 1,
                  transition: 'all 0.4s ease',
                }} />
              )
            })}
          </div>
        </div>

        {/* Steps list */}
        <div style={{ padding: '6px 0' }}>
          {steps.map((step, i) => {
            const cfg = STATUS_CONFIG[step.status] || STATUS_CONFIG.pending
            const isRunning = step.status === 'running'
            const isDone = !['pending', 'running'].includes(step.status)
            const isExpanded = expandedStep === step.step_number
            const hasFindings = step.findings && step.findings.length > 0

            return (
              <div key={i}>
                <div
                  onClick={() => hasFindings && isDone ? setExpandedStep(isExpanded ? null : step.step_number) : null}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 18px',
                    cursor: hasFindings && isDone ? 'pointer' : 'default',
                    transition: 'background 0.15s',
                    background: isExpanded ? 'var(--c-accent-faint)' : 'transparent',
                  }}
                  onMouseEnter={e => { if (hasFindings && isDone) e.currentTarget.style.background = 'var(--c-accent-faint)' }}
                  onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = 'transparent' }}
                >
                  {/* Status icon */}
                  <div style={{
                    width: 26, height: 26, borderRadius: '50%',
                    background: cfg.bg, border: `1.5px solid ${cfg.border}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 12, fontWeight: 700, color: cfg.color,
                    flexShrink: 0,
                    animation: isRunning ? 'pulse 1.5s ease-in-out infinite' : 'none',
                    transition: 'all 0.3s ease',
                  }}>
                    {cfg.icon}
                  </div>

                  {/* Step info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <span style={{
                        fontSize: 12, fontWeight: 600,
                        color: isDone ? 'var(--c-text)' : 'var(--c-text-dim)',
                        transition: 'color 0.3s',
                      }}>
                        {step.step_name}
                      </span>
                      {isDone && (
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 6,
                          background: cfg.bg, color: cfg.color, textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                        }}>
                          {cfg.label}
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: 11, color: 'var(--c-text-dim)', marginTop: 2,
                      opacity: isDone || isRunning ? 0.85 : 0.5,
                      transition: 'opacity 0.3s',
                    }}>
                      {isDone && step.findings && step.findings.length > 0
                        ? step.findings[0]
                        : (step.description || '')}
                    </div>
                  </div>

                  {/* Expand arrow */}
                  {hasFindings && isDone && (
                    <span style={{
                      fontSize: 10, color: 'var(--c-text-dim)', flexShrink: 0,
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)',
                      transition: 'transform 0.2s',
                    }}>▼</span>
                  )}
                </div>

                {/* Expanded findings */}
                {isExpanded && hasFindings && (
                  <div style={{
                    margin: '0 18px 8px 56px', padding: '8px 12px',
                    background: 'var(--c-accent-faint)',
                    borderRadius: 8, borderLeft: `2px solid ${cfg.color}`,
                  }}>
                    {step.findings.map((f, fi) => (
                      <div key={fi} style={{
                        fontSize: 11, color: 'var(--c-text-dim)', lineHeight: 1.6,
                        padding: '1px 0',
                      }}>
                        {f}
                      </div>
                    ))}
                    {step.details?.has_document_image && step.details?.image_url && (
                      <div
                        onClick={(e) => { e.stopPropagation(); setDocImageUrl(`http://localhost:8000${step.details.image_url}`); }}
                        style={{
                          marginTop: 8, padding: '6px 12px', display: 'inline-flex',
                          alignItems: 'center', gap: 6, cursor: 'pointer',
                          background: 'var(--c-blue-soft)', border: '1px solid rgba(41,98,255,0.2)',
                          borderRadius: 8, fontSize: 11, fontWeight: 600,
                          color: 'var(--c-blue)', transition: 'all 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(41,98,255,0.15)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'var(--c-blue-soft)' }}
                      >
                        🔍 View Source Document
                      </div>
                    )}

                    {/* DECREE full-evaluation affordance — Damage Documentation step only */}
                    {step.step_number === 2 && step.details?.decree && (
                      <div style={{ marginTop: 10 }}>
                        {(step.details.cost_low != null && step.details.cost_high != null) && (
                          <div style={{
                            fontSize: 11, fontWeight: 700, color: 'var(--c-text)',
                            marginBottom: 6,
                          }}>
                            ${step.details.cost_low.toLocaleString()}–${step.details.cost_high.toLocaleString()}
                            {step.details.confidence != null && (
                              <span style={{ fontWeight: 500, color: 'var(--c-text-dim)' }}>
                                {'  ·  '}{step.details.confidence}% confidence
                              </span>
                            )}
                          </div>
                        )}
                        <div
                          onClick={(e) => { e.stopPropagation(); if (!decreeBusy) onRunDecreeFull() }}
                          style={{
                            padding: '6px 12px', display: 'inline-flex',
                            alignItems: 'center', gap: 6,
                            cursor: decreeBusy ? 'default' : 'pointer',
                            background: 'var(--c-blue-soft)', border: '1px solid rgba(41,98,255,0.2)',
                            borderRadius: 8, fontSize: 11, fontWeight: 600,
                            color: 'var(--c-blue)', opacity: decreeBusy ? 0.7 : 1,
                            transition: 'all 0.15s',
                          }}
                          onMouseEnter={e => { if (!decreeBusy) e.currentTarget.style.background = 'rgba(41,98,255,0.15)' }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'var(--c-blue-soft)' }}
                        >
                          {decreeBusy
                            ? '⏳ Running in background — see 🔔'
                            : '📊 Click here for full evaluation →'}
                        </div>
                        <div style={{
                          fontSize: 9, color: 'var(--c-text-dim)', fontStyle: 'italic',
                          marginTop: 4, marginLeft: 2,
                        }}>
                          Powered by DECREE<sup>™</sup>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Separator */}
                {i < steps.length - 1 && (
                  <div style={{
                    height: 1, margin: '0 18px 0 56px',
                    background: 'var(--c-border)', opacity: 0.5,
                  }} />
                )}
              </div>
            )
          })}
        </div>

        {/* Summary footer */}
        {complete && summary && (
          <div style={{
            padding: '12px 18px',
            borderTop: '1px solid var(--c-border)',
            background: 'linear-gradient(135deg, var(--c-accent-faint) 0%, transparent 100%)',
            display: 'flex', gap: 16, alignItems: 'center',
          }}>
            {summary.passed > 0 && (
              <span style={{ fontSize: 11, fontWeight: 600, color: '#22c55e', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e' }} />
                {summary.passed} Passed
              </span>
            )}
            {summary.needs_review > 0 && (
              <span style={{ fontSize: 11, fontWeight: 600, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#f59e0b' }} />
                {summary.needs_review} Need Review
              </span>
            )}
            {summary.failed > 0 && (
              <span style={{ fontSize: 11, fontWeight: 600, color: '#ef4444', display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444' }} />
                {summary.failed} Failed
              </span>
            )}
          </div>
        )}

        {/* Launch Auto Scan button */}
        {complete && onStartAutoScan && (
          <div style={{ padding: '12px 18px', borderTop: '1px solid var(--c-border)' }}>
            <button
              onClick={() => onStartAutoScan({ steps, summary })}
              style={{
                width: '100%', padding: '11px 16px', borderRadius: 'var(--r-btn)',
                border: 'none', cursor: 'pointer',
                background: 'linear-gradient(90deg, #a100ff, #d6298a)',
                color: '#fff', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                transition: 'all 0.2s', boxShadow: '0 2px 10px rgba(161,0,255,0.28)',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 16px rgba(161,0,255,0.36)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 2px 10px rgba(161,0,255,0.28)' }}
            >
              <svg width="14" height="14" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 4V1.5A.5.5 0 011.5 1H4"/><path d="M11 1h2.5a.5.5 0 01.5.5V4"/>
                <path d="M14 11v2.5a.5.5 0 01-.5.5H11"/><path d="M4 14H1.5a.5.5 0 01-.5-.5V11"/>
                <line x1="1" y1="7.5" x2="14" y2="7.5"/>
              </svg>
              Launch AI Fraud Analysis →
            </button>
          </div>
        )}
      </div>

      {/* Document image popup modal */}
      {docImageUrl && (
        <div
          onClick={() => setDocImageUrl(null)}
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 9999, cursor: 'pointer',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'relative', maxWidth: '90vw', maxHeight: '90vh',
              background: 'var(--c-surface)', borderRadius: 12,
              boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
              overflow: 'hidden', display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Modal header */}
            <div style={{
              padding: '12px 18px', display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', borderBottom: '1px solid var(--c-border)',
              background: 'linear-gradient(135deg, rgba(59,130,246,0.08) 0%, transparent 100%)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 16 }}>📄</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--c-text)' }}>
                  Source Document
                </span>
              </div>
              <div
                onClick={() => setDocImageUrl(null)}
                style={{
                  width: 28, height: 28, borderRadius: 8, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 14, color: 'var(--c-text-dim)', fontWeight: 700,
                  background: 'rgba(100,116,139,0.1)', transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; e.currentTarget.style.color = '#ef4444' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(100,116,139,0.1)'; e.currentTarget.style.color = 'var(--c-text-dim)' }}
              >
                ✕
              </div>
            </div>
            {/* Image */}
            <div style={{ overflow: 'auto', padding: 16, cursor: 'default' }}>
              <img
                src={docImageUrl}
                alt="Claim source document"
                style={{ maxWidth: '100%', height: 'auto', borderRadius: 6 }}
              />
            </div>
          </div>
        </div>
      )}

      {/* CSS animation for running spinner */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.92); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

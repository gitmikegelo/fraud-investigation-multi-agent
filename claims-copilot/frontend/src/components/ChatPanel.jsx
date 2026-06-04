import { useState, useRef, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
  wellness: [
    { label: 'Dependent Check',  prompt: 'Check dependent anomalies for this claim' },
    { label: 'Claim History',    prompt: 'Show related claims for this member' },
  ],
  accident: [
    { label: 'Match to Policy',  prompt: 'Does this claim match the policy coverage?' },
    { label: 'State Rules',      prompt: 'Check state-specific rules for this claim' },
  ],
  hospital_indemnity: [
    { label: 'Provider Check',   prompt: 'Check provider patterns for this claim' },
    { label: 'Documents',        prompt: 'Analyze the medical documents for this claim' },
  ],
  critical_illness: [
    { label: 'Medical Records',  prompt: 'Analyze medical documentation for this claim' },
    { label: 'Policy Check',     prompt: 'Get full policy details and any alerts' },
  ],
}

export default function ChatPanel({ caseId, caseType, caseSummary, onBack, onNavigateToDossier, onStartAutoScan }) {
  const { messages, isThinking, isConnected, checklistState, checklistRunning, sendMessage, runChecklist } = useCopilotChat(caseId)
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

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
              <span style={{ fontSize: 14, fontWeight: 700, color: '#818cf8', fontFamily: 'ui-monospace, monospace' }}>
                {caseSummary?.case_id || caseId}
              </span>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-text)' }}>
                {caseSummary?.subject_name || ''}
              </span>
              <span style={{
                fontSize: 10, padding: '2px 8px', borderRadius: 10,
                background: 'rgba(99,102,241,0.12)', color: '#818cf8', fontWeight: 600,
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
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: isConnected ? '#22c55e' : '#ef4444',
          }} />
        </div>

        {/* Alert banner */}
        {(ruleCount > 0 || taskCount > 0) && (
          <div style={{
            marginTop: 8, padding: '6px 12px', borderRadius: 8,
            background: ruleCount > 0 ? 'rgba(239,68,68,0.06)' : 'rgba(99,102,241,0.06)',
            border: `1px solid ${ruleCount > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(99,102,241,0.15)'}`,
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
            ? <ChecklistCard key={i} msg={msg} onStartAutoScan={onStartAutoScan} />
            : <MessageBubble key={i} msg={msg} onNavigateToDossier={onNavigateToDossier} />
        ))}

        {isThinking && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
            background: 'rgba(99,102,241,0.06)', borderRadius: 12, alignSelf: 'flex-start',
          }}>
            <span className="animate-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#6366f1' }} />
            <span style={{ fontSize: 12, color: '#818cf8', fontStyle: 'italic' }}>Copilot is thinking…</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

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
          onMouseEnter={e => { if (!isThinking && !checklistRunning) e.currentTarget.style.borderColor = '#6366f1' }}
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
          onFocus={e => e.target.style.borderColor = '#6366f1'}
          onBlur={e => e.target.style.borderColor = 'var(--c-border)'}
        />
        <button onClick={handleSend} disabled={isThinking || !input.trim()} style={{
          padding: '10px 20px', borderRadius: 10, border: 'none',
          background: (isThinking || !input.trim()) ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.85)',
          color: (isThinking || !input.trim()) ? '#6366f1' : '#fff',
          fontSize: 13, fontWeight: 600, cursor: (isThinking || !input.trim()) ? 'not-allowed' : 'pointer',
          transition: 'all 0.15s', flexShrink: 0,
        }}>
          Send
        </button>
      </div>
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
          fontSize: 11, color: '#818cf8', background: 'rgba(99,102,241,0.06)',
          border: '1px solid rgba(99,102,241,0.15)', borderRadius: 8,
          padding: '5px 12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ fontSize: 10 }}>🔧</span>
          {msg.tool}
          <span style={{ fontSize: 9, opacity: 0.6 }}>{toolOpen ? '▲' : '▼'}</span>
        </button>
        {toolOpen && (
          <div style={{
            marginTop: 4, padding: '8px 12px', background: 'rgba(99,102,241,0.04)',
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
        color: isAnalyst ? '#818cf8' : '#64748b',
        textAlign: isAnalyst ? 'right' : 'left',
      }}>
        {isAnalyst ? 'You' : 'Copilot'}
      </div>
      <div style={{
        padding: '10px 14px', borderRadius: 12,
        background: isAnalyst ? 'rgba(99,102,241,0.12)' : 'var(--c-surface2)',
        border: isAnalyst ? '1px solid rgba(99,102,241,0.2)' : '1px solid var(--c-border)',
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
            fontSize: 12, fontWeight: 600, padding: '7px 16px', borderRadius: 8,
            background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)',
            color: '#818cf8', cursor: 'pointer', transition: 'all 0.15s', width: '100%',
            justifyContent: 'center',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.22)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.12)' }}
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
  running:      { icon: '◌', color: '#818cf8', bg: 'rgba(99,102,241,0.10)', border: 'rgba(99,102,241,0.25)', label: 'Running' },
  pending:      { icon: '○', color: '#64748b', bg: 'rgba(100,116,139,0.06)',border: 'rgba(100,116,139,0.12)',label: 'Pending' },
  error:        { icon: '⚠', color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)',   label: 'Error' },
}

function ChecklistCard({ msg, onStartAutoScan }) {
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
          background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(59,130,246,0.06) 100%)',
          borderBottom: '1px solid var(--c-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(99,102,241,0.15)',
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
                    background: isExpanded ? 'rgba(99,102,241,0.04)' : 'transparent',
                  }}
                  onMouseEnter={e => { if (hasFindings && isDone) e.currentTarget.style.background = 'rgba(99,102,241,0.04)' }}
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
                    background: 'rgba(99,102,241,0.03)',
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
                          background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
                          borderRadius: 8, fontSize: 11, fontWeight: 600,
                          color: '#3b82f6', transition: 'all 0.15s',
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(59,130,246,0.15)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(59,130,246,0.08)' }}
                      >
                        🔍 View Source Document
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
            background: 'linear-gradient(135deg, rgba(99,102,241,0.04) 0%, transparent 100%)',
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
                width: '100%', padding: '10px 16px', borderRadius: 10,
                border: 'none', cursor: 'pointer',
                background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                color: '#fff', fontSize: 13, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                transition: 'all 0.2s', boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(99,102,241,0.4)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(99,102,241,0.3)' }}
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
      `}</style>
    </div>
  )
}

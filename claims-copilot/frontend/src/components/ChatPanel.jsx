import { useState, useRef, useEffect } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useCopilotChat } from '../hooks/useCopilotChat'

const DISABILITY_CHIPS = [
  { label: 'Timeline',        prompt: 'Show me the chronological timeline for this claim' },
  { label: 'Medical Records', prompt: 'Summarize the medical documentation' },
  { label: 'History',         prompt: 'Check this claimant\'s prior claim history' },
  { label: 'Policy Details',  prompt: 'What are the policy details and risk indicators?' },
  { label: 'Red Flags',       prompt: 'What inconsistencies do you see in this claim?' },
  { label: 'Related Claims',  prompt: 'Are there other claims with the same treating provider?' },
]

const PROVIDER_CHIPS = [
  { label: 'Profile',         prompt: 'Tell me about this provider' },
  { label: 'Peer Comparison', prompt: 'How does this provider compare to peers?' },
  { label: 'Claims',          prompt: 'Show me the actual claims' },
  { label: 'Network',         prompt: 'Who is this provider connected to?' },
  { label: 'Referrals',       prompt: 'Show me the referral history' },
  { label: 'Ring Detection',  prompt: 'Are there any fraud rings involving this provider?' },
]

export default function ChatPanel({ caseId, caseType, caseSummary, onBack }) {
  const { messages, isThinking, isConnected, sendMessage } = useCopilotChat(caseId)
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const chips = caseType === 'disability_claim' ? DISABILITY_CHIPS : PROVIDER_CHIPS

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    sendMessage(text)
    setInput('')
  }

  const handleChip = (prompt) => {
    sendMessage(prompt)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Case header */}
      <div style={{
        padding: '12px 20px', background: 'var(--c-surface)',
        borderBottom: '1px solid var(--c-border)',
        display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
      }}>
        <button onClick={onBack} style={{
          background: 'transparent', border: '1px solid var(--c-border)', borderRadius: 6,
          color: 'var(--c-text-dim)', cursor: 'pointer', padding: '4px 10px', fontSize: 12,
        }}>← Queue</button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#818cf8', fontFamily: 'ui-monospace, monospace' }}>
              {caseSummary?.case_id || caseId}
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-text)' }}>
              {caseSummary?.subject_name || ''}
            </span>
            <span style={{
              fontSize: 10, padding: '2px 8px', borderRadius: 10,
              background: caseType === 'disability_claim' ? 'rgba(168,85,247,0.12)' : 'rgba(59,130,246,0.12)',
              color: caseType === 'disability_claim' ? '#c084fc' : '#60a5fa',
              fontWeight: 600,
            }}>
              {caseType === 'disability_claim' ? 'Disability' : 'Provider Fraud'}
            </span>
          </div>
          {caseSummary?.flag_reason && (
            <div style={{ fontSize: 11, color: 'var(--c-text-dim)', marginTop: 2 }}>
              {caseSummary.flag_reason}
            </div>
          )}
        </div>
        <span style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: isConnected ? '#22c55e' : '#ef4444',
        }} />
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, overflow: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}

        {isThinking && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
            background: 'rgba(99,102,241,0.06)', borderRadius: 12, alignSelf: 'flex-start',
          }}>
            <span className="animate-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: '#6366f1' }} />
            <span style={{ fontSize: 12, color: '#818cf8', fontStyle: 'italic' }}>Agent is thinking…</span>
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
          <button key={c.label} onClick={() => handleChip(c.prompt)} disabled={isThinking} style={{
            fontSize: 11, padding: '4px 12px', borderRadius: 14,
            border: '1px solid var(--c-border)', background: 'transparent',
            color: 'var(--c-text-dim)', cursor: isThinking ? 'not-allowed' : 'pointer',
            opacity: isThinking ? 0.5 : 1, transition: 'all 0.12s',
          }}
          onMouseEnter={e => { if (!isThinking) e.currentTarget.style.borderColor = '#6366f1' }}
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
          placeholder="Ask about this case…"
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


function MessageBubble({ msg }) {
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

  return (
    <div style={{
      alignSelf: isAnalyst ? 'flex-end' : 'flex-start',
      maxWidth: '80%',
    }}>
      <div style={{
        fontSize: 10, fontWeight: 600, marginBottom: 3,
        color: isAnalyst ? '#818cf8' : '#64748b',
        textAlign: isAnalyst ? 'right' : 'left',
      }}>
        {isAnalyst ? 'You' : 'ARIA Copilot'}
      </div>
      <div style={{
        padding: '10px 14px', borderRadius: 12,
        background: isAnalyst ? 'rgba(99,102,241,0.12)' : 'var(--c-surface2)',
        border: isAnalyst ? '1px solid rgba(99,102,241,0.2)' : '1px solid var(--c-border)',
        color: 'var(--c-text)', fontSize: 13, lineHeight: 1.55,
      }}>
        {isAnalyst ? (
          msg.text
        ) : (
          <div className="chat-markdown">
            <Markdown remarkPlugins={[remarkGfm]}>{msg.text}</Markdown>
          </div>
        )}
      </div>
    </div>
  )
}

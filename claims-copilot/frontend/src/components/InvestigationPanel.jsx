import { useState, useEffect, useRef, useCallback } from 'react'

const NODES = [
  { key: 'orchestrator', label: 'Orchestrator', purpose: 'Plans the work' },
  { key: 'investigator', label: 'Investigator', purpose: 'Gathers evidence' },
  { key: 'case_writer', label: 'Case writer', purpose: 'Tests the evidence' },
  { key: 'examiner', label: 'You', purpose: 'Final say' },
]
const NODE_KEY = { orchestrator: 'orchestrator', investigation: 'investigator', dossier: 'case_writer' }
const AGENT_LABEL = { orchestrator: 'Orchestrator', investigator: 'Investigator', case_writer: 'Case writer' }

// The case writer's six required checks, matched by keyword against its hold notes
const CHECKS = [
  { id: 'docs', label: 'Documents reconciled', match: /reconcil/i },
  { id: 'value', label: 'Value vs market', match: /benchmark|value/i },
  { id: 'photos', label: 'Photo integrity', match: /integrity|photo/i },
  { id: 'frequency', label: 'Claim frequency', match: /frequency/i },
  { id: 'coverage', label: 'Coverage basis', match: /coverage/i },
  { id: 'network', label: 'Surveyor independence', match: /network|independen/i },
]

const NOISE = /^(---|Calling LLM|LLM responded|Invoking LLM|Starting .*sub-agent|Phase transition|Evidence gaps:)/i

const now = () => new Date().toISOString()
const clock = (iso) => new Date(iso).toLocaleTimeString('en-GB', { hour12: false })
const sentence = (s) => s.charAt(0) + s.slice(1).toLowerCase()

function parseHold(note = '') {
  const gaps = []
  const met = []
  for (const line of note.split('\n')) {
    const g = line.match(/^\s*\d+\.\s+([A-Z][A-Z &/-]+?)\s*\(/)
    if (g) gaps.push(sentence(g[1].trim()))
    const m = line.match(/^\s*✓\s*([^:]+)/)
    if (m) met.push(m[1].trim())
  }
  return { gaps, met }
}

const panel = { background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 'var(--r-l)', overflow: 'hidden' }
const panelHead = { display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', borderBottom: '1px solid var(--line)' }
const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 8, padding: '9px 16px', borderRadius: 'var(--r-s)', fontWeight: 500, fontSize: 13.5,
  background: 'var(--grad-primary)', color: '#fff', border: '1px solid var(--accent)', boxShadow: 'var(--sh-btn)', whiteSpace: 'nowrap',
}

export default function InvestigationPanel({ claim, startRequest, onComplete, onStatus, showToast }) {
  const [status, setStatus] = useState('idle') // idle | running | complete | error
  const [nodes, setNodes] = useState({})       // key -> { status, text }
  const [passes, setPasses] = useState([])     // { summary, outcome, gaps }
  const [checks, setChecks] = useState({})     // check id -> 'met' | 'open'
  const [openGaps, setOpenGaps] = useState(0)
  const [sources, setSources] = useState(0)
  const [loopback, setLoopback] = useState(false)
  const [events, setEvents] = useState([])
  const [elapsed, setElapsed] = useState(0)
  const [steer, setSteer] = useState('')
  const wsRef = useRef(null)
  const currentNode = useRef(null)
  const logRef = useRef(null)

  useEffect(() => {
    if (status !== 'running') return
    const t0 = Date.now() - elapsed * 1000
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 1000)
    return () => clearInterval(id)
  }, [status]) // eslint-disable-line react-hooks/exhaustive-deps

  // Follow new events unless the presenter has scrolled up to read something
  const stickToBottom = useRef(true)
  const onLogScroll = () => {
    const el = logRef.current
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }
  useEffect(() => {
    const el = logRef.current
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [events])

  useEffect(() => () => wsRef.current?.close(), [])
  useEffect(() => { onStatus(status) }, [status, onStatus])

  const push = useCallback((e) => setEvents(prev => [...prev.map(x => ({ ...x, current: false })), { id: prev.length, at: now(), ...e }]), [])

  const setNode = (key, patch) => setNodes(prev => ({ ...prev, [key]: { ...prev[key], ...patch } }))

  const handle = useCallback((d) => {
    switch (d.type) {
      case 'node_enter': {
        const key = NODE_KEY[d.node]
        if (!key) return
        setNodes(prev => {
          const next = { ...prev }
          const doneText = { orchestrator: 'Routed the pass', investigator: 'Evidence gathered', case_writer: 'Assessment done' }
          for (const k of Object.keys(next)) if (next[k].status === 'active') next[k] = { status: 'done', text: doneText[k] || 'Done' }
          next[key] = { status: 'active', text: key === 'case_writer' ? 'Testing the evidence' : key === 'orchestrator' ? 'Routing the next pass' : 'Gathering evidence' }
          return next
        })
        if (key === 'investigator') {
          setPasses(prev => [...prev, { summary: 'Gathering evidence', outcome: 'running' }])
        }
        currentNode.current = key
        return
      }
      case 'node_exit':
        if (NODE_KEY[d.node] === 'investigator' && d.findings_preview) {
          const summary = d.findings_preview.replace(/\.\.\.$/, '').split('. ')[0]
          setPasses(prev => prev.map((p, i) => i === prev.length - 1 ? { ...p, summary } : p))
        }
        return
      case 'log': {
        const text = (d.message || '').trim()
        if (!text || NOISE.test(text)) return
        const agentKey = d.agent === 'tool' ? currentNode.current : NODE_KEY[(d.agent || '').toLowerCase()] || currentNode.current
        const isTool = d.agent === 'tool'
        const body = isTool ? text.replace(/^tool:\w+\s*->\s*/, '') : text
        if (isTool && body.endsWith('...')) {
          if (agentKey) setNode(agentKey, { text: body.replace(/\.\.\.$/, '').slice(0, 48) })
          return
        }
        if (isTool) setSources(n => n + 1)
        // Verdicts are shown by the hold/accept events; skip the raw tool verdict lines
        if (/Sub-agent finished|Evidence (assessed as )?(IN)?SUFFICIENT|^(IN)?SUFFICIENT \(|^Missing:|^Dossier generated/i.test(body)) return
        push({ kind: 'agent_step', agent: AGENT_LABEL[agentKey] || 'Agent', text: body, current: true })
        return
      }
      case 'dossier_rejected': {
        const { gaps, met } = parseHold(d.evidence_gaps)
        setChecks(prev => {
          const next = { ...prev }
          for (const c of CHECKS) {
            if (met.some(m => c.match.test(m))) next[c.id] = 'met'
            if (gaps.some(g => c.match.test(g))) next[c.id] = 'open'
          }
          return next
        })
        const n = gaps.length || Number((d.message || '').match(/(\d+) of \d+/)?.[1] || 1)
        setOpenGaps(n)
        setLoopback(true)
        setNode('case_writer', { status: 'holding', text: `Holding: ${n} gap${n === 1 ? '' : 's'}` })
        setPasses(prev => prev.map((p, i) => i === prev.length - 1 ? { ...p, outcome: 'gaps', gaps: n } : p))
        push({ kind: 'hold', agent: 'Case writer', text: `Case writer held the dossier — ${n} of ${CHECKS.length} required checks not met yet:`, gaps })
        return
      }
      case 'dossier_accepted':
        setChecks(Object.fromEntries(CHECKS.map(c => [c.id, 'met'])))
        setOpenGaps(0)
        setLoopback(false)
        setNode('case_writer', { status: 'done', text: 'All required checks met' })
        setPasses(prev => prev.map((p, i) => i === prev.length - 1 ? { ...p, outcome: 'complete' } : p))
        push({ kind: 'agent_step', agent: 'Case writer', text: 'accepted the dossier — all required checks met' })
        return
      case 'investigation_complete':
        setStatus('complete')
        setNodes(prev => ({
          ...prev,
          orchestrator: { status: 'done', text: `Finished after ${d.iterations} steps` },
          examiner: { status: 'active', text: 'Dossier ready for you' },
        }))
        push({ kind: 'agent_step', agent: 'Orchestrator', text: `handed the dossier to you after ${d.iterations} steps` })
        if (d.dossier) onComplete(d.dossier)
        wsRef.current?.close()
        return
      case 'error':
        setStatus('error')
        push({ kind: 'error', agent: 'System', text: d.message || 'The investigation stopped unexpectedly.' })
        return
      default:
    }
  }, [push, onComplete])

  const start = useCallback(() => {
    if (!claim?.case_id || status === 'running') return
    wsRef.current?.close()
    setStatus('running')
    setNodes({ orchestrator: { status: 'active', text: 'Planning pass 1' } })
    setPasses([]); setChecks({}); setOpenGaps(0); setSources(0); setLoopback(false); setEvents([]); setElapsed(0)
    currentNode.current = 'orchestrator'

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.hostname}:8000/ws/investigate/${claim.case_id}`)
    wsRef.current = ws
    ws.onopen = () => {
      ws.send(JSON.stringify({ action: 'start', checklist_context: null }))
      push({ kind: 'agent_step', agent: 'Orchestrator', text: `started the investigation for ${claim.subject_name}` })
    }
    ws.onmessage = (evt) => {
      try {
        const d = JSON.parse(evt.data)
        if (d.type !== 'heartbeat') handle(d)
      } catch { /* ignore malformed frames */ }
    }
    ws.onerror = () => {
      setStatus('error')
      push({ kind: 'error', agent: 'System', text: 'Lost connection to the investigation service.' })
    }
  }, [claim?.case_id, claim?.subject_name, status, handle, push])

  const lastRequest = useRef(startRequest)
  useEffect(() => {
    if (startRequest && startRequest !== lastRequest.current) start()
    lastRequest.current = startRequest
  }, [startRequest, start])

  const sendSteer = () => {
    const t = steer.trim()
    if (!t) return
    push({ kind: 'steer', agent: 'You', text: t, pass: passes.length + 1 })
    showToast('Sent to the orchestrator')
    setSteer('')
  }

  const metCount = CHECKS.filter(c => checks[c.id] === 'met').length
  const elapsedFmt = elapsed >= 60 ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s` : `${elapsed}s`
  const findings = events.filter(e => e.agent === 'Investigator' && e.kind === 'agent_step').length

  const nodeLook = (s) => ({
    done: { border: '1px solid #CBE5D6', color: 'var(--low)' },
    active: { border: '1px solid var(--accent)', boxShadow: '0 0 0 4px var(--accent-soft)', color: 'var(--accent-ink)' },
    holding: { border: '1px solid var(--med-line)', background: '#FFFCF6', color: 'var(--med)' },
  }[s] || { border: '1px solid var(--line)', color: 'var(--muted)' })

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) var(--chat-w)', gap: 18, alignItems: 'start' }}>
      <div style={panel}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600, flex: 1 }}>Agent flow</h2>
          {status === 'idle' ? (
            <button type="button" onClick={start} style={primaryBtn}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="11" cy="11" r="6.5" /><path d="M20 20l-4-4" /></svg>
              Start investigation
            </button>
          ) : (
            <span style={{ fontSize: 13, color: 'var(--muted)' }}>
              Pass {Math.max(passes.length, 1)} of up to 5 · {elapsedFmt}
            </span>
          )}
        </div>

        <div style={{ padding: '24px 24px 8px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 28 }}>
            {NODES.map((n, i) => {
              const st = nodes[n.key]?.status || 'idle'
              const look = nodeLook(st)
              return (
                <div key={n.key} style={{ position: 'relative', padding: 14, borderRadius: 'var(--r-m)', minHeight: 96, background: 'var(--surface)', ...look, color: undefined }}>
                  <small style={{ color: 'var(--muted)', fontSize: 12 }}>{n.purpose}</small>
                  <b style={{ display: 'block', fontWeight: 600, marginTop: 2, color: st === 'active' ? 'var(--accent-ink)' : 'var(--ink)' }}>{n.label}</b>
                  <div style={{ marginTop: 10, fontSize: 12.5, color: look.color, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 7, height: 7, borderRadius: '50%', background: st === 'idle' ? 'var(--line)' : 'currentColor', flexShrink: 0, animation: st === 'active' ? 'pulse 1.4s ease-in-out infinite' : 'none' }} />
                    {nodes[n.key]?.text || (n.key === 'examiner' ? 'Waiting for dossier' : 'Waiting')}
                  </div>
                  {i < NODES.length - 1 && (
                    <span style={{ position: 'absolute', right: -29, top: 48, width: 28, height: 1.5, background: st === 'active' ? 'var(--accent)' : 'var(--line)' }} />
                  )}
                </div>
              )
            })}
          </div>
          <div aria-hidden="true" style={{ position: 'relative', height: 66, visibility: loopback ? 'visible' : 'hidden' }}>
            <svg viewBox="0 0 100 54" preserveAspectRatio="none" style={{ position: 'absolute', left: 0, top: 0, width: '100%', height: 44, overflow: 'visible' }}>
              <path d="M62.5 0 V30 Q62.5 40 56 40 H44 Q37.5 40 37.5 30 V4" fill="none" stroke="#E0A43A" strokeWidth="1.5" vectorEffect="non-scaling-stroke" strokeDasharray="4 4" />
              <path d="M36.3 8 L37.5 2 L38.7 8" fill="none" stroke="#E0A43A" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            </svg>
            <span style={{ position: 'absolute', left: '37.5%', width: '25%', textAlign: 'center', bottom: 0, fontSize: 12, color: 'var(--med)', fontWeight: 500 }}>
              Sent back with {openGaps} gap{openGaps === 1 ? '' : 's'}
            </span>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--line)', padding: '16px 24px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Passes</h3>
          {passes.length === 0 && <p style={{ fontSize: 13, color: 'var(--muted)' }}>No passes yet.</p>}
          {passes.map((p, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 90px', gap: 12, padding: '8px 0', fontSize: 13, borderBottom: i < passes.length - 1 ? '1px dashed var(--line)' : 'none' }}>
              <span style={{ color: 'var(--muted)' }}>Pass {i + 1}</span>
              <span>{p.summary}</span>
              <span style={{ textAlign: 'right', color: p.outcome === 'complete' ? 'var(--low)' : p.outcome === 'gaps' ? 'var(--med)' : 'var(--accent-ink)' }}>
                {p.outcome === 'complete' ? 'Complete' : p.outcome === 'gaps' ? `${p.gaps} gaps` : 'Running'}
              </span>
            </div>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--line)', padding: '16px 24px' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Required checks · {metCount} of {CHECKS.length} met</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 24 }}>
            {CHECKS.map(c => {
              const s = checks[c.id]
              return (
                <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 13, borderBottom: '1px solid var(--line-2)' }}>
                  <span>{c.label}</span>
                  <span style={{ fontWeight: 500, color: s === 'met' ? 'var(--low)' : s === 'open' ? 'var(--med)' : 'var(--muted)' }}>
                    {s === 'met' ? 'Met' : s === 'open' ? 'Open' : '—'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', borderTop: '1px solid var(--line)' }}>
          {[['Sources checked', sources], ['Findings', findings], ['Open gaps', openGaps]].map(([label, v], i) => (
            <div key={label} style={{ padding: '14px 24px', borderRight: i < 2 ? '1px solid var(--line)' : 'none' }}>
              <small style={{ color: 'var(--muted)', fontSize: 12.5 }}>{label}</small>
              <b style={{ display: 'block', fontSize: 20, fontWeight: 600, letterSpacing: '-.02em', marginTop: 2, color: label === 'Open gaps' && v > 0 ? 'var(--med)' : 'var(--ink)' }}>{v}</b>
            </div>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--line)', padding: '16px 24px 20px', background: '#FCFAFF' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Steer the investigation</h3>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 10 }}>Add context or redirect focus. The orchestrator picks it up on the next pass.</p>
          <form onSubmit={e => { e.preventDefault(); sendSteer() }} style={{ display: 'flex', gap: 8 }}>
            <input value={steer} onChange={e => setSteer(e.target.value)} aria-label="Instruction for the investigation"
              placeholder="e.g. Also check the forwarder's other consignees"
              style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: '9px 12px', background: 'var(--canvas)', fontSize: 13 }} />
            <button type="submit" disabled={!steer.trim()} style={{ ...primaryBtn, opacity: steer.trim() ? 1 : 0.5 }}>Send to agents</button>
          </form>
        </div>
      </div>

      <div style={{ ...panel, position: 'sticky', top: 76 }}>
        <div style={panelHead}>
          <h2 style={{ fontSize: 15, fontWeight: 600, flex: 1 }}>Activity</h2>
          {status === 'running' && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 500, padding: '3px 9px', borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent-ink)' }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'currentColor', animation: 'pulse 1.4s ease-in-out infinite' }} />Live
            </span>
          )}
        </div>
        <ul ref={logRef} onScroll={onLogScroll} aria-live="polite" aria-relevant="additions" style={{ listStyle: 'none', maxHeight: 'calc(100vh - 56px - 230px)', minHeight: 420, overflowY: 'auto' }}>
          {events.length === 0 && (
            <li style={{ padding: '16px 20px', fontSize: 13, color: 'var(--muted)' }}>
              Start the investigation to see each agent step here.
            </li>
          )}
          {events.map(e => (
            <li key={e.id} style={{
              display: 'grid', gridTemplateColumns: '58px 1fr', gap: 12, padding: '10px 20px', fontSize: 13, borderBottom: '1px solid var(--line-2)',
              background: e.kind === 'hold' ? '#FFFBF3' : e.kind === 'steer' ? 'var(--accent-soft)' : e.kind === 'error' ? 'var(--high-soft)' : 'transparent',
              boxShadow: e.kind === 'hold' ? 'inset 3px 0 0 #E0A43A' : 'none',
            }}>
              <time style={{ color: 'var(--muted)', fontSize: 12, paddingTop: 1 }}>{clock(e.at)}</time>
              <div>
                <span style={{ fontWeight: 600, color: e.kind === 'hold' ? 'var(--med)' : e.kind === 'steer' ? 'var(--accent-ink)' : e.kind === 'error' ? 'var(--high)' : 'var(--ink)' }}>
                  {e.kind === 'hold' ? '' : `${e.agent} `}
                </span>
                <span>{e.text}</span>
                {e.current && status === 'running' && (
                  <span style={{ display: 'inline-block', width: 5, height: 13, background: 'var(--accent)', marginLeft: 3, verticalAlign: -2, animation: 'pulse 1s steps(1) infinite' }} />
                )}
                {e.kind === 'hold' && e.gaps.length > 0 && (
                  <ul style={{ margin: '6px 0 0 16px', color: 'var(--ink-2)', listStyle: 'disc' }}>
                    {e.gaps.map(g => <li key={g} style={{ padding: '1px 0' }}>{g}</li>)}
                  </ul>
                )}
                {e.kind === 'steer' && (
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Orchestrator will include this in pass {e.pass}</div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

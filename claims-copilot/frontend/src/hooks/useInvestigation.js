import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * Custom hook that manages the WebSocket connection and investigation state.
 * Connects to /ws/investigate/{claimId} and streams agent events.
 */
export function useInvestigation(claimId, checklistContext) {
  const [status, setStatus] = useState('idle') // idle | connecting | running | complete | error
  const [activeNode, setActiveNode] = useState(null)
  const [phase, setPhase] = useState('—')
  const [loopCount, setLoopCount] = useState(0)
  const [events, setEvents] = useState([])
  const [logs, setLogs] = useState([])
  const [dossier, setDossier] = useState('')
  const [findings, setFindings] = useState({})
  const [result, setResult] = useState(null)
  const [nodeHistory, setNodeHistory] = useState([])
  const [elapsed, setElapsed] = useState(0)

  const wsRef = useRef(null)
  const startTimeRef = useRef(null)
  const timerRef = useRef(null)

  // Elapsed timer
  useEffect(() => {
    if (status === 'running') {
      startTimeRef.current = Date.now()
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [status])

  const addEvent = useCallback((evt) => {
    setEvents(prev => [...prev, evt])
  }, [])

  const addLog = useCallback((log) => {
    setLogs(prev => [...prev, log])
  }, [])

  const handleEvent = useCallback((data) => {
    const { type, timestamp, ...rest } = data

    switch (type) {
      case 'connected':
        addEvent({ type, timestamp, message: rest.message || `Connected — ${rest.subject_name || ''}` })
        break

      case 'status':
        addEvent({ type, timestamp, message: rest.message })
        break

      case 'graph_start':
        addEvent({ type, timestamp, message: 'Investigation graph started' })
        break

      case 'node_enter':
        setActiveNode(rest.node)
        setNodeHistory(prev => [...prev, rest.node])
        addEvent({
          type, timestamp, node: rest.node,
          message: `Entering ${rest.node} (step ${rest.iteration})`,
        })
        break

      case 'node_exit':
        addEvent({
          type, timestamp, node: rest.node,
          message: `Completed ${rest.node}`,
          details: rest,
        })
        break

      case 'phase_change':
        setPhase(rest.phase)
        setLoopCount(rest.loop_count || 0)
        addEvent({
          type, timestamp,
          message: `Phase → ${rest.phase}`,
          phase: rest.phase,
        })
        break

      case 'log':
        addLog({ timestamp, agent: rest.agent, message: rest.message })
        break

      case 'dossier_rejected':
        addEvent({
          type, timestamp, node: 'dossier',
          message: rest.message || 'Dossier rejected — evidence insufficient',
          evidence_gaps: rest.evidence_gaps,
        })
        addLog({
          timestamp, agent: 'dossier',
          message: `⛔ REJECTED: ${rest.message || 'Evidence insufficient'}${rest.evidence_gaps ? '\n\nEvidence gaps:\n' + rest.evidence_gaps : ''}`,
        })
        break

      case 'dossier_accepted':
        addEvent({
          type, timestamp, node: 'dossier',
          message: rest.message || 'Dossier accepted — evidence sufficient',
        })
        addLog({
          timestamp, agent: 'dossier',
          message: `✅ ACCEPTED: ${rest.message || 'Evidence sufficient'}`,
        })
        break

      case 'investigation_complete':
        setStatus('complete')
        setActiveNode(null)
        setResult(rest)
        if (rest.dossier) setDossier(rest.dossier)
        if (rest.findings) setFindings(rest.findings)
        addEvent({
          type, timestamp,
          message: `Investigation complete — ${rest.iterations} steps in ${rest.total_time}s`,
        })
        break

      case 'error':
        setStatus('error')
        addEvent({ type, timestamp, message: rest.message })
        break

      default:
        addEvent({ type, timestamp, message: JSON.stringify(rest) })
    }
  }, [addEvent, addLog])

  const startInvestigation = useCallback(() => {
    if (!claimId) return

    // Reset state
    setStatus('connecting')
    setActiveNode('start')
    setPhase('Initializing')
    setLoopCount(0)
    setEvents([])
    setLogs([])
    setDossier('')
    setFindings({})
    setResult(null)
    setNodeHistory(['start'])
    setElapsed(0)

    const startTime = new Date().toISOString()
    setEvents([{ type: 'status', timestamp: startTime, message: 'Connecting to investigation service...' }])

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.hostname}:8000/ws/investigate/${claimId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      // Send checklist context and start action
      ws.send(JSON.stringify({
        action: 'start',
        checklist_context: checklistContext || null,
      }))
      setStatus('running')
      setPhase('Agent Orchestration')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type !== 'heartbeat') {
          handleEvent(data)
        }
      } catch (e) {
        console.error('Failed to parse WS message', e)
      }
    }

    ws.onerror = () => {
      setStatus('error')
    }

    ws.onclose = () => {}
  }, [claimId, checklistContext, handleEvent])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  return {
    status, activeNode, phase, loopCount, events, logs,
    dossier, findings, result, startInvestigation, nodeHistory, elapsed,
  }
}

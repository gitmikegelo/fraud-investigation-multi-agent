import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * Custom hook that manages the WebSocket connection and investigation state.
 */
export function useInvestigation() {
  const [status, setStatus] = useState('idle') // idle | connecting | running | complete | error
  const [activeNode, setActiveNode] = useState(null)
  const [phase, setPhase] = useState('—')
  const [loopCount, setLoopCount] = useState(0)
  const [events, setEvents] = useState([])
  const [logs, setLogs] = useState([])
  const [dossier, setDossier] = useState('')
  const [findings, setFindings] = useState({})
  const [result, setResult] = useState(null)
  const [nodeHistory, setNodeHistory] = useState([]) // ordered list of visited nodes
  const [elapsed, setElapsed] = useState(0)
  const [initialClaims, setInitialClaims] = useState([]) // initial claims being investigated

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

  const startInvestigation = useCallback(() => {
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
    setInitialClaims([])

    // Fetch initial claims being investigated
    fetch('/api/anomaly-summary')
      .then(res => res.json())
      .then(data => {
        if (data.top_providers) {
          setInitialClaims(data.top_providers)
        }
      })
      .catch(err => console.error('Failed to fetch initial claims:', err))

    // Add initial event
    const startTime = new Date().toISOString()
    setEvents([{ type: 'status', timestamp: startTime, message: 'Starting initial analysis...' }])

    // Simulate initial analysis phase (6 seconds)
    setTimeout(() => {
      setActiveNode('analysis')
      setNodeHistory(['start', 'analysis'])
      setPhase('Initial Analysis')
      setEvents(prev => [
        ...prev,
        { type: 'node_enter', timestamp: new Date().toISOString(), node: 'analysis', message: 'Running Isolation Forest anomaly detection...' },
      ])

      // Add log entries for the analysis
      setTimeout(() => {
        setLogs(prev => [...prev, { timestamp: new Date().toISOString(), agent: 'analysis', message: 'Scanning claim features with Isolation Forest model...' }])
      }, 1000)
      setTimeout(() => {
        setLogs(prev => [...prev, { timestamp: new Date().toISOString(), agent: 'analysis', message: 'Analyzing provider-patient connection graph...' }])
      }, 2500)
      setTimeout(() => {
        setLogs(prev => [...prev, { timestamp: new Date().toISOString(), agent: 'analysis', message: 'Detecting billing code anomalies...' }])
      }, 4000)
      setTimeout(() => {
        setEvents(prev => [...prev, { type: 'node_exit', timestamp: new Date().toISOString(), node: 'analysis', message: 'Initial analysis complete - anomalies detected' }])
      }, 5500)

      // After 6 seconds, connect to WebSocket and continue
      setTimeout(() => {
        connectWebSocket()
      }, 6000)
    }, 500) // Brief delay before entering analysis node
  }, [])

  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/investigate`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('running')
      setPhase('Agent Orchestration')
      ws.send(JSON.stringify({ action: 'start' }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleEvent(data)
      } catch (e) {
        console.error('Failed to parse WS message', e)
      }
    }

    ws.onerror = () => {
      setStatus('error')
    }

    ws.onclose = () => {
      if (status !== 'complete') {
        // Only set error if we didn't complete normally
      }
    }
  }, [])

  const handleEvent = useCallback((data) => {
    const { type, timestamp, ...rest } = data

    switch (type) {
      case 'connected':
        addEvent({ type, timestamp, message: rest.message })
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
          type,
          timestamp,
          node: rest.node,
          message: `Entering ${rest.node} (step ${rest.iteration})`,
        })
        break

      case 'node_exit':
        addEvent({
          type,
          timestamp,
          node: rest.node,
          message: `Completed ${rest.node}`,
          details: rest,
        })
        break

      case 'phase_change':
        setPhase(rest.phase)
        setLoopCount(rest.loop_count || 0)
        addEvent({
          type,
          timestamp,
          message: `Phase → ${rest.phase}`,
          phase: rest.phase,
        })
        break

      case 'log':
        addLog({
          timestamp,
          agent: rest.agent,
          message: rest.message,
        })
        break

      case 'dossier_rejected':
        addEvent({
          type,
          timestamp,
          node: 'dossier',
          message: rest.message || 'Dossier rejected — evidence insufficient',
          evidence_gaps: rest.evidence_gaps,
        })
        addLog({
          timestamp,
          agent: 'dossier',
          message: `⛔ REJECTED: ${rest.message || 'Evidence insufficient'}${rest.evidence_gaps ? '\n\nEvidence gaps:\n' + rest.evidence_gaps : ''}`,
        })
        break

      case 'dossier_accepted':
        addEvent({
          type,
          timestamp,
          node: 'dossier',
          message: rest.message || 'Dossier accepted — evidence sufficient',
        })
        addLog({
          timestamp,
          agent: 'dossier',
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
          type,
          timestamp,
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

  return {
    status,
    activeNode,
    phase,
    loopCount,
    events,
    logs,
    dossier,
    findings,
    result,
    startInvestigation,
    nodeHistory,
    elapsed,
    initialClaims,
  }
}

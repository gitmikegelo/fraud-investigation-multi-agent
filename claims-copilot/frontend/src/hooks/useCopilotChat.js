import { useState, useEffect, useRef, useCallback } from 'react'

export function useCopilotChat(caseId) {
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [checklistState, setChecklistState] = useState(null)
  const [checklistRunning, setChecklistRunning] = useState(false)
  const [policyAlerts, setPolicyAlerts] = useState([])
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    if (!caseId) return
    const url = `ws://${window.location.hostname}:8000/ws/chat/${caseId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (evt) => {
      let data
      try { data = JSON.parse(evt.data) } catch { return }

      switch (data.type) {
        case 'connected':
          setIsConnected(true)
          setMessages(prev => [...prev, {
            role: 'system',
            text: `Connected — ${data.subject_name} | ${data.claim_type} | Risk: ${data.risk_score} (${data.risk_tier})`,
            timestamp: data.timestamp,
          }])
          break

        case 'thinking':
          setIsThinking(true)
          break

        case 'tool_call':
          setMessages(prev => [...prev, {
            role: 'tool',
            tool: data.tool,
            toolArgs: data.args,
            text: `Calling ${data.tool}...`,
            timestamp: data.timestamp,
          }])
          break

        case 'tool_result':
          setMessages(prev => {
            const updated = [...prev]
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'tool' && updated[i].tool === data.tool) {
                updated[i] = { ...updated[i], text: data.summary || `${data.tool} completed` }
                break
              }
            }
            return updated
          })
          break

        case 'checklist_start':
          setChecklistRunning(true)
          setChecklistState({ steps: data.steps, summary: null })
          setMessages(prev => [...prev, {
            role: 'checklist',
            steps: data.steps,
            summary: null,
            complete: false,
            timestamp: data.timestamp,
          }])
          break

        case 'checklist_step':
          setChecklistState(prev => {
            if (!prev) return prev
            const steps = prev.steps.map(s =>
              s.step_number === data.step_number
                ? { ...s, ...data }
                : s
            )
            return { ...prev, steps }
          })
          // Also update the checklist message in the messages array
          setMessages(prev => {
            const updated = [...prev]
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'checklist') {
                const steps = updated[i].steps.map(s =>
                  s.step_number === data.step_number
                    ? { ...s, ...data }
                    : s
                )
                updated[i] = { ...updated[i], steps }
                break
              }
            }
            return updated
          })
          break

        case 'checklist_complete':
          setChecklistRunning(false)
          setChecklistState(data.checklist)
          setMessages(prev => {
            const updated = [...prev]
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'checklist') {
                updated[i] = {
                  ...updated[i],
                  steps: data.checklist.steps,
                  summary: data.checklist.summary,
                  complete: true,
                }
                break
              }
            }
            return updated
          })
          break

        case 'checklist_update':
          setChecklistState(data.checklist)
          break

        case 'policy_alert':
          setPolicyAlerts(prev => [...prev, data.alert])
          setMessages(prev => [...prev, {
            role: 'system',
            text: `⚠ Policy Alert: ${data.alert?.detail || 'Policy change detected'}`,
            timestamp: data.timestamp,
          }])
          break

        case 'response':
          setIsThinking(false)
          setMessages(prev => [...prev, {
            role: 'assistant',
            text: data.text,
            timestamp: data.timestamp,
          }])
          break

        case 'error':
          setIsThinking(false)
          setChecklistRunning(false)
          setMessages(prev => [...prev, {
            role: 'system',
            text: `Error: ${data.message}`,
            timestamp: data.timestamp,
          }])
          break
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      reconnectTimer.current = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          connect()
        }
      }, 3000)
    }

    ws.onerror = () => {}
  }, [caseId])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const sendMessage = useCallback((text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setMessages(prev => [...prev, {
      role: 'analyst',
      text,
      timestamp: new Date().toISOString(),
    }])
    wsRef.current.send(JSON.stringify({ action: 'message', text }))
  }, [])

  const runChecklist = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setMessages(prev => [...prev, {
      role: 'analyst',
      text: '▶ Run Full Checklist',
      timestamp: new Date().toISOString(),
    }])
    wsRef.current.send(JSON.stringify({ action: 'run_checklist' }))
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setChecklistState(null)
    setChecklistRunning(false)
    setPolicyAlerts([])
  }, [])

  return { messages, isThinking, isConnected, checklistState, checklistRunning, policyAlerts, sendMessage, runChecklist, clearMessages }
}

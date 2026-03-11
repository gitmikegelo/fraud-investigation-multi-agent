import { useState, useEffect, useRef, useCallback } from 'react'

export function useCopilotChat(caseId) {
  const [messages, setMessages] = useState([])
  const [isThinking, setIsThinking] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)

  const connect = useCallback(() => {
    if (!caseId) return
    const url = `ws://${window.location.hostname}:8000/ws/chat/${caseId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      // wait for server "connected" event
    }

    ws.onmessage = (evt) => {
      let data
      try { data = JSON.parse(evt.data) } catch { return }

      switch (data.type) {
        case 'connected':
          setIsConnected(true)
          setMessages(prev => [...prev, {
            role: 'system',
            text: `Connected to case ${data.case_id} (${data.case_type?.replace('_', ' ')})`,
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
      // reconnect after 3s
      reconnectTimer.current = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          connect()
        }
      }, 3000)
    }

    ws.onerror = () => {
      // onclose will fire after this
    }
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

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return { messages, isThinking, isConnected, sendMessage, clearMessages }
}

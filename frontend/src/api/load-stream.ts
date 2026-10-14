import { connectLoads } from './loads'
import type { LoadStreamParams } from './loads'
import type { LoadView, LoadStreamEvent, SystemStatus } from './types'

export interface LiveLoadsState {
  loads: LoadView[] | null
  system: SystemStatus | null
  connection: 'connecting' | 'live' | 'reconnecting'
  error: string | null
}

// Every snapshot, update, and heartbeat contains the complete order list.
export function subscribeLoads(
  params: LoadStreamParams,
  onChange: (state: LiveLoadsState) => void,
): () => void {
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined
  let heartbeatTimer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  let retryDelay = 1000
  let loads: LoadView[] | null = null
  let system: SystemStatus | null = null
  let error: string | null = null

  function reconnect() {
    if (disposed) return
    clearTimeout(heartbeatTimer)
    onChange({ loads, system, connection: 'reconnecting', error: error ?? 'Connection lost. Reconnecting automatically…' })
    reconnectTimer = setTimeout(connect, retryDelay)
    retryDelay = Math.min(retryDelay * 2, 30_000)
  }

  function connect() {
    if (disposed) return
    error = null

    try {
      socket = connectLoads(params)
    } catch {
      error = 'Unable to connect. Retrying automatically…'
      reconnect()
      return
    }

    const currentSocket = socket

    function waitForHeartbeat() {
      clearTimeout(heartbeatTimer)
      // The server sends a heartbeat every 30 seconds, even without changes.
      heartbeatTimer = setTimeout(() => {
        error = 'Updates paused. Reconnecting automatically…'
        currentSocket.close()
      }, 45_000)
    }

    currentSocket.onopen = waitForHeartbeat
    currentSocket.onmessage = (event) => {
      if (disposed) return
      try {
        const message: LoadStreamEvent = JSON.parse(event.data)
        if (message.event === 'loads.error') {
          error = message.message
          currentSocket.close()
          return
        }

        if (!['loads.snapshot', 'loads.updated', 'loads.heartbeat'].includes(message.event)
          || !Array.isArray(message.items) || !message.system) {
          throw new Error('Invalid order message')
        }

        loads = message.items
        system = message.system
        retryDelay = 1000
        error = null
        waitForHeartbeat()
        onChange({ loads, system, connection: 'live', error: null })
      } catch {
        error = 'Unable to read order updates. Reconnecting automatically…'
        currentSocket.close()
      }
    }
    currentSocket.onerror = () => currentSocket.close()
    currentSocket.onclose = reconnect
  }

  connect()

  return () => {
    disposed = true
    clearTimeout(reconnectTimer)
    clearTimeout(heartbeatTimer)
    if (socket) {
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      socket.close()
    }
  }
}

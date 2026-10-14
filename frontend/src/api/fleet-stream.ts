import { getFleetData } from './fleet'
import type { FleetData } from './fleet'
import { subscribeLoads } from './load-stream'
import { subscribeTerminalStatuses } from './terminal-stream'

export interface LiveFleetState {
  data: FleetData | null
  connection: 'connecting' | 'live' | 'reconnecting'
  updating: boolean
  error: string | null
  revision: number
}

export function subscribeFleet(onChange: (state: LiveFleetState) => void): () => void {
  const controller = new AbortController()
  let disposed = false
  let updating = false
  let queued = false
  let data: FleetData | null = null
  let requestError: string | null = null
  let revision = 0
  const streams = {
    terminals: { connection: 'connecting', error: null },
    orders: { connection: 'connecting', error: null },
  } as Record<'terminals' | 'orders', { connection: LiveFleetState['connection']; error: string | null }>

  function publish() {
    const values = Object.values(streams)
    const connection = values.every((stream) => stream.connection === 'live') ? 'live'
      : values.some((stream) => stream.connection === 'reconnecting') ? 'reconnecting' : 'connecting'
    if (!disposed) onChange({ data, updating, revision, connection, error: requestError ?? values.find((stream) => stream.error)?.error ?? null })
  }

  async function refresh() {
    if (disposed) return
    if (updating) { queued = true; return }
    updating = true
    publish()
    try {
      const result = await getFleetData({ signal: controller.signal })
      if (disposed) return
      data = result
      revision += 1
      requestError = null
    } catch (cause) {
      if (!disposed) requestError = cause instanceof Error ? cause.message : 'Unable to load fleet data.'
    } finally {
      updating = false
      if (!disposed) {
        publish()
        if (queued) { queued = false; void refresh() }
      }
    }
  }

  // Populate immediately, including when a WebSocket is temporarily unavailable.
  void refresh()
  const stopTerminals = subscribeTerminalStatuses((state) => {
    streams.terminals = { connection: state.connection, error: state.error }
    if (state.connection === 'live') void refresh()
    else publish()
  })
  const stopOrders = subscribeLoads({ order_type: 'all', status: 'all' }, (state) => {
    streams.orders = { connection: state.connection, error: state.error }
    if (state.connection === 'live') void refresh()
    else publish()
  })

  return () => {
    disposed = true
    queued = false
    controller.abort()
    stopTerminals()
    stopOrders()
  }
}

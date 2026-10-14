import { getBidLogs } from './bids'
import { subscribeLoads } from './load-stream'
import type { BidView } from './types'

export interface LiveBidLogsState {
  bids: BidView[] | null
  connection: 'connecting' | 'live' | 'reconnecting'
  updating: boolean
  error: string | null
}

// Order events trigger a read of bid metadata, which is not in the load stream.
export function subscribeBidLogs(onChange: (state: LiveBidLogsState) => void): () => void {
  const controller = new AbortController()
  let disposed = false
  let updating = false
  let refreshQueued = false
  let bids: BidView[] | null = null
  let connection: LiveBidLogsState['connection'] = 'connecting'
  let streamError: string | null = null
  let requestError: string | null = null

  function publish() {
    if (!disposed) onChange({ bids, connection, updating, error: streamError ?? requestError })
  }

  async function refreshLogs() {
    if (disposed) return
    if (updating) {
      // Serialize reads and coalesce bursts of events into one follow-up read.
      refreshQueued = true
      return
    }
    updating = true
    publish()
    try {
      const result = await getBidLogs({ signal: controller.signal })
      if (disposed) return
      bids = result
      requestError = null
    } catch (cause) {
      if (disposed) return
      requestError = cause instanceof Error ? cause.message : 'Unable to update bid logs.'
    } finally {
      updating = false
      if (!disposed) {
        publish()
        if (refreshQueued) {
          refreshQueued = false
          void refreshLogs()
        }
      }
    }
  }

  const unsubscribe = subscribeLoads({ order_type: 'open_bid', status: 'all' }, (state) => {
    if (disposed) return
    connection = state.connection
    streamError = state.error
    if (state.connection === 'live') {
      // Includes snapshots on reconnect and heartbeats for metadata-only changes.
      void refreshLogs()
    } else {
      publish()
    }
  })

  return () => {
    disposed = true
    refreshQueued = false
    controller.abort()
    unsubscribe()
  }
}

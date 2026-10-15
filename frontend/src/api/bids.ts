import { apiFetch, withQuery } from './client'
import { endpoints } from './endpoints'
import { getLoads, subscribeLoads } from './orders'
import type { BidView, LoadView, Page, PaginationParams } from './types'

export async function getBids(
  params: PaginationParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.bids, params), { ...options, method: 'GET' })
}

// Include closed orders even when they expired or were declined without a bid.
export async function getBidLogs(options: RequestInit = {}): Promise<BidView[]> {
  const bids: BidView[] = []
  let offset = 0

  while (true) {
    const response = await getBids({ limit: 200, offset }, options)
    if (!response.ok) throw new Error(`Unable to load bid logs (HTTP ${response.status}).`)
    const page: Page<BidView> = await response.json()
    if (!Array.isArray(page.items) || !Number.isFinite(page.total)) {
      throw new Error('The bid log response was invalid.')
    }
    bids.push(...page.items)
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) break
  }

  const records = new Map(bids.map((bid) => [bid.order.external_id, bid]))
  offset = 0
  while (true) {
    const response = await getLoads({ status: 'all', include_missing: true, limit: 200, offset }, options)
    if (!response.ok) throw new Error(`Unable to load order history (HTTP ${response.status}).`)
    const page: Page<LoadView> = await response.json()
    if (!Array.isArray(page.items) || !Number.isFinite(page.total)) {
      throw new Error('The order history response was invalid.')
    }
    for (const order of page.items) {
      const bid = records.get(order.external_id)
      records.set(order.external_id, bid ? { ...bid, order } : {
        action_id: null,
        bid_rate: null,
        request_status: null,
        outcome: order.order_type === 'fixed_rate' ? 'not_applicable' : 'not_recorded',
        decision_at: order.bid_decision_at,
        order,
      })
    }
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) break
  }

  return [...records.values()].filter((bid) => ['fixed_rate', 'open_bid'].includes(bid.order.order_type) && bid.order.status !== 'open')
}

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

  const unsubscribe = subscribeLoads({ order_type: 'all', status: 'all' }, (state) => {
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

export type { BidRequest, BidView } from './types'

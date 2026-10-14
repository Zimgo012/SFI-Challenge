import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import { getLoads } from './loads'
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
    const response = await getLoads({ order_type: 'open_bid', status: 'all', include_missing: true, limit: 200, offset }, options)
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
        outcome: 'not_recorded',
        decision_at: order.bid_decision_at,
        order,
      })
    }
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) break
  }

  return [...records.values()].filter((bid) => bid.order.order_type === 'open_bid' && bid.order.status !== 'open')
}

export type { BidView, BidRequest } from './types'

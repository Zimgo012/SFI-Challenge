import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { ActionRequest, BidRequest, PaginationParams } from './types'

export type OrderType = 'fixed_rate' | 'open_bid'
export type LoadStatus = 'open' | 'accepted' | 'declined' | 'bid_submitted' | 'bid_lost' | 'in_transit' | 'completed' | 'expired'

export interface LoadParams extends PaginationParams {
  order_type?: OrderType
  status?: LoadStatus | 'all'
  origin_terminal?: string
  include_missing?: boolean
}

export async function getLoads(
  params: LoadParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.loads.list, params), { ...options, method: 'GET' })
}

export async function getLoad(
  externalId: string,
  options: RequestInit = {},
) {
  return apiFetch(endpoints.loads.detail(externalId), { ...options, method: 'GET' })
}

export async function acceptLoad(
  externalId: string,
  body: ActionRequest = {},
  options: RequestInit = {},
) {
  return apiFetch(endpoints.loads.accept(externalId), {
    ...options,
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function declineLoad(
  externalId: string,
  body: ActionRequest = {},
  options: RequestInit = {},
) {
  return apiFetch(endpoints.loads.decline(externalId), {
    ...options,
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function bidOnLoad(
  externalId: string,
  body: BidRequest,
  options: RequestInit = {},
) {
  return apiFetch(endpoints.loads.bid(externalId), {
    ...options,
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export type { ActionRequest, ActionResult, BidRequest, LoadDetail, LoadView } from './types'

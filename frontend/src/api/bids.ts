import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { PaginationParams } from './types'

export async function getBids(
  params: PaginationParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.bids, params), { ...options, method: 'GET' })
}

export type { BidView, BidRequest } from './types'

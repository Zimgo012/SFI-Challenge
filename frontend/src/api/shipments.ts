import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { PaginationParams } from './types'

export async function getShipments(
  params: PaginationParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.shipments, params), { ...options, method: 'GET' })
}

export type { LoadView } from './types'

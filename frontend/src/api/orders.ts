import { apiFetch } from './client'
import { endpoints } from './endpoints'

export async function getOrderExpiration(
  externalId: string,
  options: RequestInit = {},
) {
  return apiFetch(endpoints.orderExpiration(externalId), { ...options, method: 'GET' })
}

export type { OrderExpiration } from './types'

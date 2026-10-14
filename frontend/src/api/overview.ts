import { apiFetch } from './client'
import { endpoints } from './endpoints'

export async function getOverview(
  options: RequestInit = {},
) {
  return apiFetch(endpoints.overview, { ...options, method: 'GET' })
}

export type { Overview, ProfitSummary } from './types'

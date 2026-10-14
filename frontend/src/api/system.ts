import { apiFetch } from './client'
import { endpoints } from './endpoints'

export async function getSystemStatus(
  options: RequestInit = {},
) {
  return apiFetch(endpoints.systemStatus, { ...options, method: 'GET' })
}

export type { SystemStatus } from './types'

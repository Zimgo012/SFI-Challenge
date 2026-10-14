import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { PaginationParams } from './types'

export interface ActivityParams extends PaginationParams {
  external_id?: string
  event_type?: string
}

export async function getActivity(
  params: ActivityParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.activity, params), { ...options, method: 'GET' })
}

export type { ActivityView } from './types'

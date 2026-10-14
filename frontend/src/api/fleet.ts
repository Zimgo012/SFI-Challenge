import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { PaginationParams } from './types'

export interface FleetParams extends PaginationParams {
  terminal?: string
  status?: string
  include_missing?: boolean
}

export interface CapacityParams {
  discrepancies_only?: boolean
}

export async function getFleetUnits(
  params: FleetParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.fleet.units, params), { ...options, method: 'GET' })
}

export async function getFleetUnit(
  unitId: string,
  options: RequestInit = {},
) {
  return apiFetch(endpoints.fleet.unit(unitId), { ...options, method: 'GET' })
}

export async function getFleetCapacity(
  params: CapacityParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.fleet.capacity, params), { ...options, method: 'GET' })
}

export async function getLegacyFleetCapacity(
  params: CapacityParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.fleet.legacyCapacity, params), { ...options, method: 'GET' })
}

export type { CapacityCounts, FleetCapacityResponse, UnitDetail, UnitView } from './types'

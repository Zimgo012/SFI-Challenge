import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import { getSystemStatus } from './system'
import type { Page, PaginationParams, SystemStatus, UnitProjection, UnitView } from './types'

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

export async function getFleetProjections(
  params: { at?: string } = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.fleet.projections, params), { ...options, method: 'GET' })
}

export async function getUnitProjection(
  unitId: string,
  params: { at?: string } = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.fleet.projection(unitId), params), { ...options, method: 'GET' })
}

export interface FleetData {
  units: UnitView[]
  projections: UnitProjection[]
  system: SystemStatus
}

export async function getAllFleetUnits(options: RequestInit = {}): Promise<UnitView[]> {
  const units: UnitView[] = []
  let offset = 0
  while (true) {
    const response = await getFleetUnits({ limit: 200, offset }, options)
    if (!response.ok) throw new Error(`Unable to load fleet units (HTTP ${response.status}).`)
    const page: Page<UnitView> = await response.json()
    if (!Array.isArray(page.items) || !Number.isFinite(page.total)) throw new Error('Invalid fleet response.')
    units.push(...page.items)
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) break
  }
  return [...new Map(units.map((unit) => [unit.unit_id, unit])).values()]
}

export async function getFleetData(options: RequestInit = {}): Promise<FleetData> {
  const [units, systemResponse] = await Promise.all([getAllFleetUnits(options), getSystemStatus(options)])
  if (!systemResponse.ok) throw new Error(`Unable to load simulation time (HTTP ${systemResponse.status}).`)
  const system: SystemStatus = await systemResponse.json()
  const response = await getFleetProjections({ at: system.sim_time_utc ?? undefined }, options)
  if (!response.ok) throw new Error(`Unable to load fleet schedules (HTTP ${response.status}).`)
  const projections: UnitProjection[] = await response.json()
  if (!Array.isArray(projections)) throw new Error('Invalid fleet schedule response.')
  return { units, system, projections }
}

export type { CapacityCounts, FleetCapacityResponse, UnitDetail, UnitProjection, UnitView } from './types'

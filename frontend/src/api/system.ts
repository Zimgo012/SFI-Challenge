import { apiFetch } from './client'
import { endpoints } from './endpoints'

export async function getSystemStatus(
  options: RequestInit = {},
) {
  return apiFetch(endpoints.systemStatus, { ...options, method: 'GET' })
}

export async function getSimulationClock(options: RequestInit = {}) {
  if (!import.meta.env.DEV) throw new Error('Temporary simulation controls are available in local development only.')
  return apiFetch(endpoints.simulationClock, { ...options, method: 'GET' })
}

export async function setSimulationSpeed(speed: number, options: RequestInit = {}) {
  if (!import.meta.env.DEV) throw new Error('Temporary simulation controls are available in local development only.')
  if (!Number.isFinite(speed) || speed < 1 || speed > 100_000) {
    throw new Error('Simulation speed must be between 1 and 100,000.')
  }
  return apiFetch(endpoints.simulationClock, {
    ...options,
    method: 'POST',
    body: JSON.stringify({ simulation_speed: speed }),
  })
}

export type { SimulationClock, SystemStatus } from './types'

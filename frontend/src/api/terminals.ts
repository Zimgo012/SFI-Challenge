import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { PaginationParams } from './types'
import { env } from '../config/env'

export async function getTerminals(
  params: PaginationParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.terminals.list, params), { ...options, method: 'GET' })
}

export async function getTerminal(
  code: string,
  options: RequestInit = {},
) {
  return apiFetch(endpoints.terminals.detail(code), { ...options, method: 'GET' })
}

export async function getTerminalStatuses(
  options: RequestInit = {},
) {
  return apiFetch(endpoints.terminals.status, { ...options, method: 'GET' })
}

// Close on unmount and reconnect after closure. Each message replaces the status list.
export function connectTerminalStatus(): WebSocket {
  const url = new URL(
    `${env.apiBaseUrl}${endpoints.terminals.statusWebSocket}`,
    window.location.origin,
  )
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(url)
}

export type { TerminalDetail, TerminalStatus, TerminalStatusEvent, TerminalStatusMessage, TerminalView } from './types'

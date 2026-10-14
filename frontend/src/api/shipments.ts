import { apiFetch } from './client'
import { endpoints } from './endpoints'
import { withQuery } from './request'
import type { LoadView, Page, PaginationParams } from './types'

export async function getShipments(
  params: PaginationParams = {},
  options: RequestInit = {},
) {
  return apiFetch(withQuery(endpoints.shipments, params), { ...options, method: 'GET' })
}

export async function getAllShipments(options: RequestInit = {}): Promise<LoadView[]> {
  const shipments: LoadView[] = []
  let offset = 0
  while (true) {
    const response = await getShipments({ limit: 200, offset }, options)
    if (!response.ok) throw new Error(`Unable to load shipments (HTTP ${response.status}).`)
    const page: Page<LoadView> = await response.json()
    if (!Array.isArray(page.items) || !Number.isFinite(page.total)) throw new Error('Invalid shipment response.')
    shipments.push(...page.items)
    offset += page.items.length
    if (page.items.length === 0 || offset >= page.total) break
  }
  return [...new Map(shipments.map((shipment) => [shipment.external_id, shipment])).values()]
}

export type { LoadView } from './types'

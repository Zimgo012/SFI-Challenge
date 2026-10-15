import type { LoadView } from '../api/shipments'

export type ShipmentStatus = 'all' | 'accepted' | 'in_transit' | 'completed'
export type ShipmentSort = 'created' | 'pickup' | 'delivery' | 'synced'

export function confirmedShipments(loads: LoadView[]) {
  return loads.filter((load) => ['accepted', 'in_transit', 'completed'].includes(load.status) && !load.board_missing_at)
}

export function filterShipments(shipments: LoadView[], search: string, status: ShipmentStatus) {
  const query = search.trim().toLowerCase()
  return confirmedShipments(shipments).filter((shipment) =>
    (status === 'all' || shipment.status === status)
    && (!query || [shipment.external_id, shipment.origin_terminal_code, shipment.destination_terminal_code,
      shipment.origin_city, shipment.destination_city, shipment.assigned_terminal_code, shipment.board_assigned_unit_id?.toString()]
      .some((value) => value?.toLowerCase().includes(query))),
  )
}

export function sortShipments(shipments: LoadView[], field: ShipmentSort, direction: 'asc' | 'desc') {
  const dateKey = { created: 'board_created_at', pickup: 'pickup_at', delivery: 'delivery_at', synced: 'last_synced_at' } as const
  return [...shipments].sort((a, b) => {
    const leftDate = a[dateKey[field]]
    const rightDate = b[dateKey[field]]
    const left = leftDate ? Date.parse(leftDate) : NaN
    const right = rightDate ? Date.parse(rightDate) : NaN
    if (Number.isFinite(left) !== Number.isFinite(right)) return Number.isFinite(left) ? -1 : 1
    const delta = Number.isFinite(left) && Number.isFinite(right) ? left - right : 0
    return (direction === 'asc' ? delta : -delta) || a.external_id.localeCompare(b.external_id, undefined, { numeric: true })
  })
}

export function isDeliveryOverdue(shipment: LoadView, simTime: string | null): boolean {
  return shipment.status !== 'completed' && !!simTime && !!shipment.delivery_at
    && Date.parse(simTime) > Date.parse(shipment.delivery_at)
}

export function shipmentStage(status: string) {
  return ['accepted', 'in_transit', 'completed'].indexOf(status)
}

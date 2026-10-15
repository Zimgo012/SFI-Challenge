export const activityEventTypes = [
  'action.requested', 'action.succeeded', 'action.failed', 'action.unknown', 'action.reconciled',
  'order.ingested', 'order.status_changed', 'order.expired',
  'assignment.confirmed', 'assignment.cancelled', 'assignment.conflict',
  'fleet.discrepancy', 'fleet.reconciled', 'reservation.released', 'sync.error',
]

export function activityColor(eventType: string) {
  const suffix = eventType.split('.').at(-1)
  if (suffix === 'error' || suffix === 'failed') return 'badge-error'
  if (suffix === 'unknown' || suffix === 'conflict' || suffix === 'discrepancy') return 'badge-warning'
  if (suffix === 'succeeded' || suffix === 'confirmed' || suffix === 'reconciled') return 'badge-success'
  return 'badge-neutral'
}

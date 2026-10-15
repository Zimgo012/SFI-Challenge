type ObjectValue = Record<string, unknown>
function object(value: unknown): ObjectValue {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as ObjectValue : {}
}

const reasonMessages: Record<string, string> = {
  maximum_weight_exceeded: 'The cargo exceeds the allowed weight limit.',
  minimum_margin_usd_not_met: 'The expected profit is below the required minimum.',
  minimum_margin_pct_not_met: 'The profit margin is below the required minimum.',
  no_terminal_capacity_for_window: 'No unit is available at the pickup terminal for this schedule.',
  no_available_units_at_pickup_terminal: 'No unit is available at the pickup terminal.',
  offer_expired: 'This offer has expired.',
  order_not_open: 'This order is no longer open.',
  order_missing_from_board: 'This order is no longer available on the board.',
  unknown_origin_terminal_code: 'The pickup terminal could not be found.',
  pickup_terminal_unresolved: 'The pickup terminal could not be identified.',
  assignment_window_overlap: 'The unit already has an assignment during this schedule.',
  unit_schedule_unavailable: 'The unit is unavailable for the full pickup and delivery schedule.',
  maximum_deadhead_exceeded: 'The pickup is too far from the available unit.',
  cannot_reach_pickup_in_time: 'The unit cannot reach the pickup on time.',
  terminal_snapshot_stale: 'Terminal availability needs to be refreshed.',
  unit_snapshot_stale_or_unknown: 'Fleet availability needs to be refreshed.',
  terminal_capacity_discrepancy: 'Fleet availability does not match the board. Refresh the fleet data.',
}

export function readableMessage(value: string): string {
  const trimmed = value.trim()
  if (reasonMessages[trimmed]) return reasonMessages[trimmed]
  if (/^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/.test(trimmed)) {
    const words = trimmed.replaceAll('_', ' ')
    return `${words[0].toUpperCase()}${words.slice(1)}.`
  }
  return trimmed.replace(/^Dispatch rejected:\s*/i, '')
    .replace(/\s*\([a-z][a-z0-9]*(?:_[a-z0-9]+)+\)/g, '')
    .replace(/\bbid_rate\b/g, 'bid amount')
    .replace(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g, (code) => reasonMessages[code] ?? code.replaceAll('_', ' '))
}

function primaryCause(evaluation: ObjectValue, rawDetail: unknown): string | undefined {
  const reasons = Array.isArray(evaluation.rejection_details) ? evaluation.rejection_details.map(object) : []
  const codes = new Set([
    ...reasons.map((reason) => reason.code),
    ...(Array.isArray(evaluation.rejection_reasons) ? evaluation.rejection_reasons : []),
    ...(typeof rawDetail === 'string' ? [...rawDetail.matchAll(/\(([a-z][a-z0-9_]+)\)/g)].map((match) => match[1]) : []),
  ])
  const has = (...values: string[]) => values.some((value) => codes.has(value))
  if (has('offer_expired')) return 'This offer has expired.'
  if (has('order_missing_from_board', 'order_not_open')) return 'This offer is no longer available.'
  if (has('unknown_origin_terminal_code', 'pickup_terminal_unresolved')) return 'Pickup terminal not found.'
  if (has('maximum_weight_exceeded')) return 'Cargo exceeds the allowed weight limit.'
  if (has('terminal_capacity_discrepancy')) return 'Truck availability is out of sync with the board.'
  if (has('terminal_snapshot_stale', 'unit_snapshot_stale_or_unknown')) return 'Truck availability needs a fresh update.'
  const conflictingSchedule = reasons.some((reason) => {
    const context = object(reason.context)
    return reason.check === 'schedule_passed' && (
      (Array.isArray(context.conflicting_assignments) && context.conflicting_assignments.length > 0)
      || (Array.isArray(context.conflicting_reservations) && context.conflicting_reservations.length > 0)
    )
  })
  if (has('assignment_window_overlap', 'assignment_window_reserved') || conflictingSchedule) return 'Truck schedule overlaps another assignment or reservation.'
  if (has('no_terminal_capacity_for_window', 'no_available_units_at_pickup_terminal')) return 'No truck available for this booking window.'
  if (has('unit_missing_from_board')) return 'No eligible truck can be confirmed for this offer.'
  if (has('unit_status_unavailable', 'unit_unavailable_at_pickup', 'projected_unit_unavailable', 'unit_schedule_unavailable')) return 'Truck unavailable for this schedule.'
  if (has('maximum_deadhead_exceeded', 'pickup_move_exceeds_limit', 'projected_pickup_move_exceeds_limit')) return 'Pickup is too far from the available truck.'
  if (has('cannot_reach_pickup_in_time', 'insufficient_pickup_lead_time', 'departure_in_past')) return 'The truck cannot reach pickup on time.'
  if (has('minimum_margin_usd_not_met', 'minimum_margin_pct_not_met')) return 'Profit is below the required minimum.'
  if (has('projected_location_unavailable', 'projected_pickup_terminal_mismatch', 'unit_not_board_selectable')) return 'No eligible truck can be confirmed at the pickup terminal.'
  if (has('expected_margin_unknown', 'loaded_cost_unknown_or_invalid', 'cost_per_mile_unknown_or_invalid')) return 'Profit cannot be calculated from the available costs.'
}

export function apiFeedback(payload: unknown, status: number) {
  const body = object(payload)
  const evaluation = object(body.evaluation)
  const feedback = object(body.feedback)
  const details: string[] = []
  const suggestions: string[] = []
  const add = (items: string[], value: unknown) => {
    if (typeof value === 'string' && value.trim()) {
      const text = readableMessage(value)
      if (!items.includes(text)) items.push(text)
    }
  }
  for (const value of Array.isArray(evaluation.rejection_details) ? evaluation.rejection_details : []) {
    const reason = object(value)
    add(details, reason.message)
    add(suggestions, reason.suggested_action)
  }
  if (!details.length) {
    for (const reason of Array.isArray(evaluation.rejection_reasons) ? evaluation.rejection_reasons : []) add(details, reason)
  }
  const rejectionMessage = details[0]
  // Keep the board's direct rejection ahead of ancillary capacity warnings.
  const directMessage = typeof body.detail === 'string' && body.detail.trim() ? readableMessage(body.detail) : undefined
  for (const value of Array.isArray(evaluation.capacity_warnings) ? evaluation.capacity_warnings : []) {
    const warning = object(value)
    add(details, warning.message)
    add(suggestions, warning.suggested_action)
  }
  if (Array.isArray(body.detail)) {
    for (const value of body.detail) {
      const validation = object(value)
      const location = Array.isArray(validation.loc) ? validation.loc : []
      const field = location.includes('bid_rate') ? 'Bid amount' : 'Input'
      add(details, location.includes('bid_rate') ? 'Bid amount must be positive and use no more than two decimal places.' : `${field}: ${typeof validation.msg === 'string' ? validation.msg : 'Check this value.'}`)
    }
  }
  add(suggestions, feedback.suggested_action)
  const fallback = status === 404 ? 'This order could not be found. Refresh the board and choose an available offer.'
    : status === 422 ? 'Check the entered values before trying again.'
    : status === 409 ? 'The order could not be submitted because its availability or eligibility changed.'
    : status >= 500 ? 'The service could not confirm the request. Check the order status before trying again.'
    : 'The request could not be completed. Refresh the order and try again.'
  const message = primaryCause(evaluation, body.detail) ?? rejectionMessage ?? directMessage ?? details[0] ?? fallback
  if (directMessage && !rejectionMessage && directMessage !== message) add(details, body.detail)
  return { message, details: details.filter((detail) => detail !== message), suggestions }
}

export type LoadFeedback = {
  id: string
  title: string
  message: string
  tone: 'success' | 'warning' | 'error' | 'info'
  details?: string[]
  suggestions?: string[]
}

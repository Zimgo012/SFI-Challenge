// Mirrors dispatcher Pydantic response schemas in backend/schema/.
// Decimal values and UTC timestamps are serialized as strings.
export type DecimalString = string

export interface Page<T> {
  items: Array<T>
  total: number
  limit: number
  offset: number
}

export interface AssignmentView {
  assignment_id: string
  shipment_id: string
  unit_id: string
  origin_terminal_id: string
  destination_terminal_id: string
  busy_from: string
  busy_until: string
  assignment_status: string
  confirmed_at: string
  completed_at: string | null
}

export interface ActionView {
  action_id: string
  shipment_id: string
  evaluation_id: string | null
  action_type: string
  bid_rate: DecimalString | null
  carrier_note: string | null
  request_status: string
  board_http_status: number | null
  board_message: string | null
  requested_at: string
  resolved_at: string | null
}

export interface EvaluationView {
  evaluation_id: string
  shipment_id: string
  candidate_unit_id: string | null
  payout: DecimalString | null
  loaded_cost: DecimalString | null
  deadhead_miles: DecimalString | null
  deadhead_cost: DecimalString | null
  total_cost: DecimalString | null
  profit_usd: DecimalString | null
  margin_pct: DecimalString | null
  suggested_bid: DecimalString | null
  cost_source: string | null
  pricing_passed: boolean
  capacity_passed: boolean
  schedule_passed: boolean
  weight_passed: boolean
  location_passed: boolean
  offer_open_unexpired: boolean
  eligible: boolean
  rejection_reasons: Record<string, unknown> | unknown[]
  policy_snapshot: Record<string, unknown> | unknown[]
  evaluated_at_sim: string
  evaluated_at_wall: string
}

export interface LoadView {
  shipment_id: string
  external_id: string
  board_order_id: number | null
  order_type: string
  status: string
  origin_terminal_code: string | null
  destination_terminal_code: string | null
  origin_terminal_id: string | null
  destination_terminal_id: string | null
  origin_city: string | null
  origin_state: string | null
  origin_latitude: DecimalString | null
  origin_longitude: DecimalString | null
  destination_city: string | null
  destination_state: string | null
  destination_latitude: DecimalString | null
  destination_longitude: DecimalString | null
  distance_miles: DecimalString | null
  weight_lbs: number | null
  offered_rate: DecimalString | null
  cost_per_mile: DecimalString | null
  estimated_cost: DecimalString | null
  estimated_deadhead_miles: DecimalString | null
  estimated_deadhead_cost: DecimalString | null
  estimated_total_cost: DecimalString | null
  pickup_at: string | null
  delivery_at: string | null
  expires_at: string | null
  board_created_at: string | null
  bid_decision_at: string | null
  winning_bid_rate: DecimalString | null
  board_assigned_unit_id: number | null
  assigned_terminal_code: string | null
  last_synced_at: string | null
  board_missing_at: string | null
  seconds_remaining: number | null
  estimated_profit: DecimalString | null
  profit_category: string
}

export interface UnitView {
  unit_id: string
  board_unit_id: number
  home_terminal_id: string
  unit_number: string
  employee_code: string
  first_name: string
  last_name: string
  status: string
  current_latitude: DecimalString | null
  current_longitude: DecimalString | null
  available_at: string | null
  last_synced_at: string | null
  board_missing_at: string | null
  terminal_code: string | null
  current_terminal_id: string | null
  current_terminal_code: string | null
  next_terminal_id: string | null
  next_terminal_code: string | null
}

export interface TerminalView {
  terminal_id: string
  board_terminal_id: number
  code: string
  name: string
  city: string
  state: string
  latitude: DecimalString | null
  longitude: DecimalString | null
  seeded_unit_capacity: number
  last_synced_at: string | null
  capacity: FleetCapacityResponse | null
}

export interface ActivityView {
  event_id: string
  shipment_id: string | null
  action_id: string | null
  event_type: string
  message: string
  details: Record<string, unknown>
  occurred_at_wall: string
  occurred_at_sim: string | null
  external_id: string | null
}

export interface LoadDetail extends LoadView {
  actions: Array<ActionView>
  actual_assignment: AssignmentView | null
  latest_evaluation: EvaluationView | null
}

export interface UnitDetail extends UnitView {
  actual_assignment: AssignmentView | null
}

export interface TerminalDetail extends TerminalView {
  roster: Array<UnitView>
}

export interface BidView {
  action_id: string | null
  bid_rate: DecimalString | null
  request_status: string | null
  outcome: string
  decision_at: string | null
  order: LoadView
}

export interface SystemStatus {
  sim_time_utc: string | null
  simulation_speed: DecimalString | null
  connection_status: string
  connection_changed_at: string | null
  last_sync_at: string | null
  last_error: string | null
}

export interface ProfitSummary {
  confirmed_estimated_profit: DecimalString
  conditional_pending_bid_profit: DecimalString
  confirmed_estimated_count: number
  pending_estimated_count: number
  confirmed_unknown_count: number
  pending_unknown_count: number
}

export interface Overview {
  counts: Record<string, number>
  profit: ProfitSummary
  loads: Array<LoadView>
  bids: Array<BidView>
  terminals: Array<TerminalView>
  fleet: Array<UnitView>
  shipments: Array<LoadView>
  activity: Array<ActivityView>
}

export interface ActionResult {
  action: ActionView
  order: LoadDetail
  sync_pending: boolean
}

export interface TerminalStatus {
  terminal_id: string
  code: string
  name: string
  city: string
  state: string
  latitude: DecimalString | null
  longitude: DecimalString | null
  status: 'available' | 'unavailable' | 'empty' | 'attention' | 'unknown'
  total_units: number | null
  available_units: number | null
  assigned_units: number | null
  board_total_units: number | null
  board_available_units: number | null
  board_assigned_units: number | null
  consistent: boolean | null
  discrepancies: Array<Record<string, unknown>>
  as_of_sim_time: string | null
  last_synced_at: string | null
}

export interface TerminalStatusMessage {
  event: 'terminals.snapshot' | 'terminals.updated' | 'terminals.heartbeat'
  revision: number
  sent_at: string
  items: Array<TerminalStatus>
}

export interface CapacityCounts {
  total_units: number
  available_units: number
  assigned_units: number
}

export interface FleetCapacityResponse {
  terminal_code: string
  board: CapacityCounts | null
  local: CapacityCounts
  consistent: boolean
  discrepancies: Array<Record<string, unknown>>
  as_of_sim_time: string
  checked_at: string
}

export interface OrderExpiration {
  external_id: string
  status: string
  expires_at: string | null
  seconds_remaining: number | null
  sim_time_utc: string
  board_missing_at: string | null
}

export interface HealthResponse {
  status: 'ok'
}

export interface ActionRequest {
  carrier_note?: string | null
}

export interface BidRequest extends ActionRequest {
  bid_rate: DecimalString | number
}

export interface TerminalStatusError {
  event: 'terminals.error'
  message: string
}

export type TerminalStatusEvent = TerminalStatusMessage | TerminalStatusError

export interface PaginationParams {
  limit?: number
  offset?: number
}

export interface LoadStreamMessage {
  event: 'loads.snapshot' | 'loads.updated' | 'loads.heartbeat'
  revision: number
  sent_at: string
  items: LoadView[]
  system: SystemStatus
}

export interface LoadStreamError {
  event: 'loads.error'
  message: string
}

export type LoadStreamEvent = LoadStreamMessage | LoadStreamError

export interface ProjectedDelivery {
  assignment_id: string
  shipment_id: string
  external_id: string
  pickup_at: string
  delivery_at: string
  terminal_id: string | null
  terminal_code: string | null
  terminal_resolution: 'destination_code' | 'nearest_destination' | 'unresolved'
  latitude: DecimalString | null
  longitude: DecimalString | null
}

export interface UnitProjection {
  unit_id: string
  board_unit_id: number
  baseline_sim_time: string | null
  at: string | null
  status: 'available' | 'busy' | 'unavailable' | 'unknown'
  terminal_id: string | null
  terminal_code: string | null
  latitude: DecimalString | null
  longitude: DecimalString | null
  available_at: string | null
  source: 'snapshot' | 'booked_delivery' | 'in_transit' | 'unknown'
  source_assignment_id: string | null
  next_terminal_id: string | null
  next_terminal_code: string | null
  deliveries: ProjectedDelivery[]
  uncertain_action_ids: string[]
  rejection_reasons: string[]
}

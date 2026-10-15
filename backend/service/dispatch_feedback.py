from schema.dispatch_policy import DispatchRejection

# Stable codes remain suitable for filtering; messages/actions can be displayed
# directly by clients. Group aliases that describe the same recovery step.
REASONS = {}


def register(codes, message, action):
    for code in codes.split():
        REASONS[code] = (message, action)


register('order_missing_from_board', 'The order is no longer present on the board.',
         'Refresh the order board and choose a currently published offer.')
register('order_not_open', 'The order is not open for dispatch.',
         'Refresh its lifecycle status; choose an open offer instead of resubmitting.')
register('offer_expired', 'The offer has expired in simulated time.',
         'Refresh the live offers and choose an unexpired order.')
register('offer_expiry_unknown', 'The offer expiration time is unknown.',
         'Sync the order expiration from the board before retrying.')
register('maximum_weight_exceeded', 'The load exceeds the configured weight limit.',
         'Choose a load within the weight limit; correct the source weight if it is inaccurate.')
register('weight_unknown_or_invalid', 'A positive load weight is required.',
         'Sync a valid weight in pounds from the source order before dispatching.')
register('minimum_margin_usd_not_met minimum_margin_pct_not_met',
         'The expected margin is below the configured minimum.',
         'For an open bid, raise the entered rate and evaluate again; otherwise choose a higher-paying offer or lower-cost route.')
register('expected_margin_unknown', 'Expected margin cannot be verified from the available cost and payout inputs.',
         'Resolve the missing cost, payout, or selected-unit location inputs and evaluate again.')
register('entered_bid_required entered_bid_invalid', 'A positive entered bid is required to evaluate this open-bid order.',
         'Enter the proposed bid_rate and request a new evaluation.')
register('offered_rate_unknown_or_invalid zero_payout_percentage_undefined', 'The offered payout is missing, invalid, or zero.',
         'Sync a positive fixed-rate payout from the board or choose another offer.')
register('cost_per_mile_unknown_or_invalid loaded_cost_unknown_or_invalid loaded_distance_unknown_or_invalid', 'Required loaded-cost or cost-per-mile data is missing or invalid.',
         'Sync valid cost inputs; loaded cost requires estimated_cost or distance_miles and cost_per_mile.')
register('maximum_deadhead_exceeded pickup_move_exceeds_limit projected_pickup_move_exceeds_limit',
         'The unit-to-pickup distance exceeds the configured maximum.',
         'Choose an offer closer to the board-selectable unit or wait for a verified closer unit position.')
register('deadhead_distance_unknown deadhead_distance_unknown_or_invalid', 'The empty travel distance cannot be verified.',
         'Sync valid pickup coordinates and the selected unit location or confirmed prior delivery destination.')
register('booking_times_unknown pickup_time_unknown delivery_time_unknown', 'Pickup and delivery timestamps are required.',
         'Sync both booking timestamps from the source order before retrying.')
register('invalid_pickup_delivery_window', 'Delivery must be later than pickup.',
         'Correct the source booking times and sync the order again.')
register('insufficient_pickup_lead_time', 'Pickup is too soon or already past in simulated time.',
         'Choose a later pickup that meets the configured minimum lead time.')
register('cannot_reach_pickup_in_time', 'The unit cannot reach pickup by the scheduled time.',
         'Choose a later pickup or an offer closer to the unit; include travel and the configured pickup buffer.')
register('occupied_window_unknown', 'The full travel, shipment, and turnaround window cannot be verified.',
         'Sync pickup/delivery times and the projected unit position before reserving the unit.')
register('departure_in_past', 'The required deadhead departure is already past in simulated time.',
         'Choose a later pickup or a closer unit so deadhead travel can start before pickup.')
register('pickup_arrival_unknown', 'The pickup arrival time cannot be verified.',
         'Sync the unit availability and projected location before evaluating travel time again.')
register('assignment_window_overlap unit_schedule_unavailable', 'The selected unit cannot be verified as free for the full booking window.',
         'Review conflicting assignment IDs and intervals; choose a non-overlapping pickup/delivery window.')
register('assignment_window_reserved', 'Another dispatch submission already holds this unit/window.',
         'Wait for that action to reconcile, then refresh availability; do not submit a duplicate reservation.')
register('unit_status_unavailable unit_unavailable_at_pickup projected_unit_unavailable',
         'The unit is unavailable or off duty at pickup.',
         'Refresh fleet status and choose an offer with a verified available unit.')
register('unit_available_after_pickup unit_availability_unknown unit_available_after_departure', 'The unit availability is unknown or later than pickup.',
         'Sync availability or choose pickup after the unit becomes available.')
register('unit_not_board_selectable future_terminal_not_yet_board_selectable',
         'The requested unit cannot currently be selected by the board at this pickup hub.',
         'Use the current board-style candidate or wait for re-homing to appear in a fresh fleet snapshot.')
register('unit_missing_from_board', 'No present board unit can be verified for this offer.',
         'Sync the current fleet roster and reevaluate an offer with available capacity.')
register('unit_snapshot_stale_or_unknown terminal_snapshot_stale', 'The fleet snapshot is too old or its sync time is unknown.',
         'Complete a fresh fleet snapshot sync before retrying; a preview does not refresh the board.')
register('no_terminal_capacity_for_window no_available_units_at_pickup_terminal',
         'No verified pickup-terminal unit is available for the requested booking window.',
         'Review roster availability, active assignments, and pending holds; choose another window or pickup hub.')
register('terminal_capacity_unknown', 'The pickup terminal capacity has not been verified.',
         'Sync the terminal roster and capacity counts before dispatching.')
register('terminal_capacity_discrepancy', 'Board capacity counts or terminal membership disagree with the local roster.',
         'Run a fresh fleet reconciliation and resolve the reported counts or hub membership before retrying.')
register('unknown_origin_terminal_code pickup_terminal_unresolved', 'The pickup terminal cannot be resolved from the current fleet hubs.',
         'Correct the origin hub code or sync the missing terminal; off-pin origins require valid coordinates.')
register('pickup_coordinates_unknown_or_invalid', 'Pickup coordinates are missing or invalid.',
         'Sync latitude between -90 and 90 and longitude between -180 and 180 from the source order.')
register('available_unit_coordinates_unknown_or_invalid unit_coordinates_unknown_or_invalid projected_location_unknown',
         'A potential board-selected unit has no verified position.',
         'Sync valid unit coordinates and confirmed delivery destinations before retrying.')
register('fleet_projection_time_unknown projection_before_fleet_snapshot',
         'The fleet snapshot cannot support a projection at the requested pickup time.',
         'Sync the fleet and simulation clock together, then choose pickup at or after the snapshot time.')
register('projected_location_unavailable projected_pickup_terminal_mismatch prior_assignment_destination_unverified booked_destination_unknown projected_destination_unknown unresolved_submission_location',
         'The unit projected location or pickup hub cannot be verified.',
         'Reconcile earlier submissions and confirmed delivery destinations, then refresh the fleet projection.')


def rejection_detail(code, check, context):
    message, action = REASONS.get(code, (
        'The dispatcher could not verify this local eligibility check.',
        'Refresh order and fleet data and review the reported check and context before retrying.',
    ))
    return DispatchRejection(code=code, check=check, message=message,
                             suggested_action=action, context=context)


def add_feedback(result, shipment, routing, capacity, unit, reason_checks):
    common = {
        'external_id': shipment.external_id, 'unit_id': result.candidate_unit_id,
        'pickup_terminal_code': routing.pickup_terminal_code,
    }
    contexts = {
        'offer_open_unexpired': {'status': shipment.status, 'expires_at': shipment.expires_at,
                                'simulated_now': result.evaluated_at_sim},
        'weight_passed': {'weight_lbs': shipment.weight_lbs, 'max_weight_lbs': result.policy.max_weight_lbs},
        'pricing_passed': {'expected_margin_usd': result.economics.gross_profit,
                           'expected_margin_pct': result.margin_pct_for_policy,
                           'min_expected_margin_usd': result.policy.min_expected_margin_usd,
                           'min_expected_margin_pct': result.policy.min_expected_margin_pct,
                           'missing_inputs': result.economics.missing_reasons},
        'deadhead_passed': {'deadhead_miles': result.deadhead_miles,
                            'max_deadhead_miles': result.policy.max_deadhead_miles},
        'timing_passed': {'pickup_at': shipment.pickup_at, 'delivery_at': shipment.delivery_at,
                          'earliest_pickup_at': result.earliest_pickup_at,
                          'occupied_window': result.occupied_window.model_dump(mode='json') if result.occupied_window else None,
                          'simulated_now': result.evaluated_at_sim,
                          'min_pickup_lead_minutes': result.policy.min_pickup_lead_minutes,
                          'pickup_buffer_minutes': result.policy.pickup_buffer_minutes},
        'location_passed': {'projected_terminal_code': result.projection.terminal_code if result.projection else None,
                            'unit_last_synced_at': unit.last_synced_at if unit else None,
                            'max_snapshot_age_seconds': result.policy.max_fleet_snapshot_age_seconds,
                            'unverified_assignment_ids': result.projection.unverified_assignment_ids if result.projection else [],
                            'uncertain_action_ids': result.projection.uncertain_action_ids if result.projection else []},
        'schedule_passed': {'pickup_at': shipment.pickup_at, 'delivery_at': shipment.delivery_at,
                            'conflicting_assignments': [], 'conflicting_reservations': [],
                            'unit_status': unit.status if unit else None,
                            'unit_available_at': unit.available_at if unit else None},
        'capacity_passed': {'capacity_units_for_window': result.capacity_units_for_window,
                            'snapshot_checked_at': capacity.checked_at if capacity else None,
                            'max_snapshot_age_seconds': result.policy.max_fleet_snapshot_age_seconds,
                            'board_total_units': capacity.board_total_units if capacity else None,
                            'board_available_units': capacity.board_available_units if capacity else None,
                            'board_assigned_units': capacity.board_assigned_units if capacity else None},
    }
    selected = next((item for item in routing.units if item.unit_id == result.candidate_unit_id), None)
    if selected:
        for field in ('conflicting_assignments', 'conflicting_reservations'):
            contexts['schedule_passed'][field] = [item.model_dump(mode='json') for item in getattr(selected, field)]
    for code, check in reason_checks.items():
        result.rejection_details.append(rejection_detail(code, check, common | contexts[check]))
    for warning in result.capacity_warnings:
        warning.update({
            'message': 'Fleet reconciliation reported a capacity or roster discrepancy.',
            'suggested_action': 'Refresh the fleet snapshot and review the reported roster and count differences.',
            'blocking': warning.get('kind') in ('roster_terminal_mismatch', 'terminal_missing_from_snapshot', 'preflight_capacity_discrepancy'),
            'pickup_terminal_code': routing.pickup_terminal_code,
        })
    for detail in result.rejection_details:
        if detail.check == 'capacity_passed':
            result.capacity_warnings.append({
                'kind': detail.code, 'message': detail.message, 'suggested_action': detail.suggested_action,
                'blocking': True, 'context': detail.context,
            })

from decimal import Context, Decimal, ROUND_HALF_UP, localcontext

from schema.economics import EconomicsSource, ExpectedEconomics, MissingEconomicsInput

CENT = Decimal('0.01')
CALCULATION_CONTEXT = Context(prec=50, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def non_negative(value) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= 0


def source(method, formula=None, **inputs):
    return EconomicsSource(method=method, formula=formula,
                           inputs={key: str(value) if value is not None else None for key, value in inputs.items()})


def missing(result, field, code, message):
    result.missing_inputs.append(MissingEconomicsInput(field=field, code=code, message=message))


def expected_economics(shipment, deadhead_miles: Decimal | None, bid_rate: Decimal | None = None,
                       *, projection=None) -> ExpectedEconomics:
    """Pure USD estimate with fixed Decimal arithmetic and auditable input sources.

    Distances are unrounded projected miles supplied by routing. No board
    deadhead/total estimate, stored winning bid, I/O, or policy threshold is used.
    """
    with localcontext(CALCULATION_CONTEXT):
        return _calculate(shipment, deadhead_miles, bid_rate, projection)


def _calculate(shipment, deadhead_miles, bid_rate, projection):
    result = ExpectedEconomics()
    if non_negative(deadhead_miles):
        result.projected_deadhead_miles = deadhead_miles
        if projection is not None:
            result.sources.projected_deadhead_miles = source(
                'selected_unit_haversine', 'haversine(projected_position, pickup_coordinates)',
                **{'unit_id': projection.unit_id, 'position_source': projection.source,
                   'source_assignment_id': projection.source_assignment_id,
                   'projection.latitude': projection.latitude, 'projection.longitude': projection.longitude,
                   'order.origin_latitude': shipment.origin_latitude, 'order.origin_longitude': shipment.origin_longitude},
            )
        else:
            result.sources.projected_deadhead_miles = source('provided_projected_deadhead_miles',
                                                            projected_deadhead_miles=deadhead_miles)
    else:
        missing(result, 'projected_deadhead_miles', 'deadhead_distance_unknown_or_invalid',
                'Provide a finite, nonnegative distance from the selected unit projected position to pickup.')

    if non_negative(shipment.cost_per_mile):
        result.cost_per_mile = shipment.cost_per_mile
        result.sources.cost_per_mile = source('board_cost_per_mile', **{'order.cost_per_mile': shipment.cost_per_mile})
    else:
        missing(result, 'order.cost_per_mile', 'cost_per_mile_unknown_or_invalid',
                'A finite, nonnegative per-mile operating cost is required for deadhead and loaded-cost fallback.')
    if result.cost_per_mile is not None and result.projected_deadhead_miles is not None:
        result.projected_deadhead_cost = money(deadhead_miles * result.cost_per_mile)
        result.sources.projected_deadhead_cost = source(
            'projected_miles_times_cost_per_mile', 'projected_deadhead_miles * cost_per_mile',
            projected_deadhead_miles=deadhead_miles, cost_per_mile=result.cost_per_mile,
        )

    if non_negative(shipment.estimated_cost):
        result.loaded_cost = money(shipment.estimated_cost)
        result.sources.loaded_cost = source('board_loaded_cost', **{'order.estimated_cost': shipment.estimated_cost})
    elif shipment.estimated_cost is None and non_negative(shipment.distance_miles) and result.cost_per_mile is not None:
        result.loaded_cost = money(shipment.distance_miles * result.cost_per_mile)
        result.sources.loaded_cost = source('distance_times_cost_per_mile', 'order.distance_miles * cost_per_mile',
                                          **{'order.distance_miles': shipment.distance_miles, 'cost_per_mile': result.cost_per_mile})
    else:
        missing(result, 'order.estimated_cost', 'loaded_cost_unknown_or_invalid',
                'Provide valid loaded cost, or omit it and supply loaded miles and cost per mile. Invalid supplied cost cannot use fallback.')
        if shipment.estimated_cost is None and not non_negative(shipment.distance_miles):
            missing(result, 'order.distance_miles', 'loaded_distance_unknown_or_invalid',
                    'Finite, nonnegative loaded miles are required when loaded cost is absent.')

    if result.loaded_cost is not None and result.projected_deadhead_cost is not None:
        result.total_cost = result.loaded_cost + result.projected_deadhead_cost
        result.sources.total_cost = source('sum_loaded_and_deadhead_cost', 'loaded_cost + projected_deadhead_cost',
                                           loaded_cost=result.loaded_cost, projected_deadhead_cost=result.projected_deadhead_cost)

    if shipment.order_type == 'fixed_rate':
        if non_negative(shipment.offered_rate):
            result.payout = money(shipment.offered_rate)
            result.sources.payout = source('fixed_rate_offer', **{'order.offered_rate': shipment.offered_rate})
        else:
            missing(result, 'order.offered_rate', 'offered_rate_unknown_or_invalid', 'Provide a finite, nonnegative fixed offer payout.')
    elif shipment.order_type == 'open_bid':
        if bid_rate is None:
            missing(result, 'bid_rate', 'entered_bid_required', 'Enter the proposed total bid payout to calculate profit.')
        elif non_negative(bid_rate) and bid_rate > 0:
            result.payout = money(bid_rate)
            result.sources.payout = source('entered_bid', bid_rate=bid_rate)
        else:
            missing(result, 'bid_rate', 'entered_bid_invalid', 'The entered total bid payout must be positive and finite.')
    else:
        missing(result, 'order.order_type', 'unsupported_order_type', 'Use fixed_rate or open_bid economics.')

    if result.payout == 0:
        missing(result, 'payout', 'zero_payout_percentage_undefined', 'Percentage margin is undefined for a zero cent-valued payout.')
    if result.payout is not None and result.total_cost is not None:
        result.gross_profit = result.payout - result.total_cost
        result.sources.gross_profit = source('payout_minus_total_cost', 'payout - total_cost',
                                             payout=result.payout, total_cost=result.total_cost)
        if result.payout > 0:
            result.margin_pct = money(result.gross_profit / result.payout * Decimal('100'))
            result.sources.margin_pct = source('profit_divided_by_payout', '100 * gross_profit / payout',
                                              gross_profit=result.gross_profit, payout=result.payout)
    return result

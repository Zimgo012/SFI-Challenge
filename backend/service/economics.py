from decimal import Decimal, ROUND_HALF_UP

from schema.economics import ExpectedEconomics

CENT = Decimal('0.01')


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def non_negative(value) -> bool:
    return value is not None and value.is_finite() and value >= 0


def expected_economics(shipment, deadhead_miles: Decimal, bid_rate: Decimal | None = None) -> ExpectedEconomics:
    """Estimate candidate costs without substituting board deadhead/total costs."""
    result = ExpectedEconomics()
    if non_negative(shipment.cost_per_mile):
        result.cost_per_mile = shipment.cost_per_mile
        if non_negative(deadhead_miles):
            result.deadhead_cost = money(deadhead_miles * shipment.cost_per_mile)
        else:
            result.missing_reasons.append('deadhead_distance_unknown_or_invalid')
    else:
        result.missing_reasons.append('cost_per_mile_unknown_or_invalid')

    if non_negative(shipment.estimated_cost):
        result.loaded_cost = money(shipment.estimated_cost)
        result.loaded_cost_source = 'board_loaded_cost'
    elif shipment.estimated_cost is None and non_negative(shipment.distance_miles) and result.cost_per_mile is not None:
        result.loaded_cost = money(shipment.distance_miles * result.cost_per_mile)
        result.loaded_cost_source = 'distance_times_cost_per_mile'
    else:
        result.missing_reasons.append('loaded_cost_unknown_or_invalid')

    if result.loaded_cost is not None and result.deadhead_cost is not None:
        result.expected_total_cost = result.loaded_cost + result.deadhead_cost

    if shipment.order_type == 'fixed_rate':
        if non_negative(shipment.offered_rate):
            result.expected_payout = money(shipment.offered_rate)
            result.payout_source = 'fixed_rate_offer'
        else:
            result.missing_reasons.append('offered_rate_unknown_or_invalid')
    elif shipment.order_type == 'open_bid':
        if bid_rate is None:
            result.missing_reasons.append('entered_bid_required')
        elif non_negative(bid_rate) and bid_rate > 0:
            result.expected_payout = money(bid_rate)
            result.payout_source = 'entered_bid'
        else:
            result.missing_reasons.append('entered_bid_invalid')
    else:
        result.missing_reasons.append('unsupported_order_type')

    if result.expected_payout == 0:
        result.missing_reasons.append('zero_payout_percentage_undefined')
    if result.expected_payout is not None and result.expected_total_cost is not None:
        result.expected_margin_usd = result.expected_payout - result.expected_total_cost
        if result.expected_payout > 0:
            result.expected_margin_pct = money(result.expected_margin_usd / result.expected_payout * Decimal('100'))
    return result

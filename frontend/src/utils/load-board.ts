import type { LoadView, OrderType } from '../api/orders'

export function getLoadOpportunities(loads: LoadView[], orderType: OrderType | 'all' = 'all') {
  return loads.filter((load) =>
    (load.order_type === 'open_bid' || load.order_type === 'fixed_rate')
    && load.status === 'open'
    && !load.board_missing_at
    && (orderType === 'all' || load.order_type === orderType),
  )
}

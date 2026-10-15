import type { LoadView } from '../api/orders'

export function getBidOpportunities(loads: LoadView[]) {
  return loads.filter((load) =>
    load.order_type === 'open_bid'
    && load.status === 'open',
  )
}

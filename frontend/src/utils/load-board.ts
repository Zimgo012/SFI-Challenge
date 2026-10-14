import type { LoadView } from '../api/types'

export function getBidOpportunities(loads: LoadView[]) {
  return loads.filter((load) =>
    load.order_type === 'open_bid'
    && load.status === 'open',
  )
}

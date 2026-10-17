import { getActivity } from './activity'
import { getLoads, subscribeLoads } from './orders'
import { getSystemStatus } from './system'
import type { ActivityView, LoadView, Page, SystemStatus } from './types'

export interface AnalyticsState {
  orders: LoadView[] | null
  requests: ActivityView[] | null
  system: SystemStatus | null
  updating: boolean
  connection: 'connecting' | 'live' | 'reconnecting'
  error: string | null
  updatedAt: string | null
}

export const initialAnalyticsState: AnalyticsState = {
  orders: null, requests: null, system: null, updating: false,
  connection: 'connecting', error: null, updatedAt: null,
}

async function allPages<T>(read: (offset: number) => Promise<Response>, key: (item: T) => string, name: string) {
  const items = new Map<string, T>()
  let offset = 0
  while (true) {
    const response = await read(offset)
    if (!response.ok) throw new Error(`${name} could not be loaded (HTTP ${response.status}).`)
    const page: Page<T> = await response.json()
    if (!Array.isArray(page.items) || !Number.isInteger(page.total) || page.total < 0) throw new Error(`${name} returned an invalid response.`)
    for (const item of page.items) items.set(key(item), item)
    offset += page.items.length
    if (offset >= page.total || !page.items.length) {
      if (offset < page.total) throw new Error(`${name} returned incomplete history. Refresh to try again.`)
      return [...items.values()]
    }
  }
}

export function getAnalyticsOrders(options: RequestInit = {}) {
  return allPages<LoadView>(offset => getLoads({ status: 'all', include_missing: true, limit: 200, offset }, options), item => item.external_id, 'Order history')
}

export function getAnalyticsRequests(options: RequestInit = {}) {
  return allPages<ActivityView>(offset => getActivity({ event_type: 'action.requested', limit: 200, offset }, options), item => item.event_id, 'Bid activity')
}

export function subscribeAnalytics(onChange: (state: AnalyticsState) => void) {
  const controller = new AbortController()
  const state = { ...initialAnalyticsState }
  let disposed = false, queued = false, revision = 0
  let streamError: string | null = null
  let requestError: string | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  const publish = () => { if (!disposed) onChange({ ...state, error: requestError ?? streamError }) }

  async function refresh() {
    if (disposed) return
    clearTimeout(timer)
    timer = undefined
    if (state.updating) { queued = true; return }
    state.updating = true
    publish()
    const before = revision
    const results = await Promise.allSettled([
      // The stream excludes missing board orders. REST retains the full history.
      getAnalyticsOrders({ signal: controller.signal }),
      getAnalyticsRequests({ signal: controller.signal }),
      getSystemStatus({ signal: controller.signal }).then(async response => {
        if (!response.ok) throw new Error('Simulation time could not be refreshed.')
        const system: SystemStatus = await response.json()
        if (!('sim_time_utc' in system)) throw new Error('Invalid simulation status.')
        return system
      }),
    ])
    if (disposed) return
    const [orders, requests, system] = results
    if (orders.status === 'fulfilled') state.orders = orders.value
    if (requests.status === 'fulfilled') state.requests = requests.value
    if (system.status === 'fulfilled' && before === revision) state.system = system.value
    const errors = results.flatMap(result => result.status === 'rejected' ? [result.reason instanceof TypeError ? 'Unable to connect to analytics. Check the backend connection.' : result.reason instanceof Error ? result.reason.message : 'Analytics could not be refreshed.'] : [])
    requestError = [...new Set(errors)].join(' ') || null
    if (!requestError) state.updatedAt = new Date().toISOString()
    state.updating = false
    publish()
    if (queued) { queued = false; schedule() }
  }

  function schedule() {
    if (!disposed && !timer) timer = setTimeout(() => { void refresh() }, 500)
  }

  const stop = subscribeLoads({ order_type: 'all', status: 'all' }, update => {
    if (disposed) return
    state.connection = update.connection
    streamError = update.error
    if (update.system) { state.system = update.system; revision++ }
    publish()
    if (update.connection === 'live') schedule()
  })
  void refresh()
  const poll = setInterval(() => { void refresh() }, 30_000)
  const onChangeHistory = () => { void refresh() }
  window.addEventListener('history-cleaned', onChangeHistory)
  window.addEventListener('simulation-speed-updated', onChangeHistory)
  return {
    refresh: () => { void refresh() },
    unsubscribe: () => {
      disposed = true
      controller.abort()
      clearTimeout(timer)
      clearInterval(poll)
      window.removeEventListener('history-cleaned', onChangeHistory)
      window.removeEventListener('simulation-speed-updated', onChangeHistory)
      stop()
    },
  }
}

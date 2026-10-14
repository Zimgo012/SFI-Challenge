import { getAllShipments } from './shipments'
import { subscribeLoads } from './load-stream'
import type { LoadView, SystemStatus } from './types'
import { confirmedShipments } from '../utils/shipments'

export interface LiveShipmentsState {
  shipments: LoadView[] | null
  system: SystemStatus | null
  connection: 'connecting' | 'live' | 'reconnecting'
  error: string | null
  revision: number
}

export function subscribeShipments(onChange: (state: LiveShipmentsState) => void): () => void {
  const controller = new AbortController()
  let disposed = false
  let receivedSnapshot = false
  let shipments: LoadView[] | null = null
  let system: SystemStatus | null = null
  let connection: LiveShipmentsState['connection'] = 'connecting'
  let streamError: string | null = null
  let requestError: string | null = null
  let revision = 0

  function publish() {
    if (!disposed) onChange({ shipments, system, connection, revision, error: streamError ?? requestError })
  }

  // Populate even while connecting. A later REST response cannot overwrite live data.
  void getAllShipments({ signal: controller.signal }).then((items) => {
    if (disposed || receivedSnapshot) return
    shipments = confirmedShipments(items)
    revision += 1
    publish()
  }).catch((cause: unknown) => {
    if (disposed || receivedSnapshot) return
    requestError = cause instanceof Error ? cause.message : 'Unable to load shipments.'
    publish()
  })

  const unsubscribe = subscribeLoads({ order_type: 'all', status: 'all' }, (state) => {
    if (disposed) return
    connection = state.connection
    streamError = state.error
    if (state.connection === 'live' && state.loads !== null) {
      receivedSnapshot = true
      shipments = confirmedShipments(state.loads)
      system = state.system
      requestError = null
      revision += 1
    }
    publish()
  })

  return () => {
    disposed = true
    controller.abort()
    unsubscribe()
  }
}

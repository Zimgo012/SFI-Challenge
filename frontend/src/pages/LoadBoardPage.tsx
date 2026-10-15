import { useEffect, useRef, useState } from 'react'
import { LoadDecisionError, getLoad, submitLoadDecision, subscribeLoads } from '../api/orders'
import type { LiveLoadsState, LoadDetail, LoadView } from '../api/orders'
import { getBidOpportunities } from '../utils/load-board'
import EmptyPanel from '../components/EmptyPanel'
import LoadCard from '../components/LoadCard'
import LoadDetailsPanel from '../components/LoadDetailsPanel'
import PageSection from '../components/PageSection'

const initialState: LiveLoadsState = {
  loads: null,
  system: null,
  connection: 'connecting',
  error: null,
}

export default function LoadBoardPage() {
  const [{ loads: streamedLoads, system, connection, error }, setStream] = useState(initialState)
  const loads = streamedLoads === null ? null : getBidOpportunities(streamedLoads)
  const [selected, setSelected] = useState<{ load: LoadView; bid: boolean } | null>(null)
  const [decisions, setDecisions] = useState<Record<string, 'submitting' | 'sent' | 'uncertain'>>({})
  const lockedOrders = useRef(new Set<string>())
  const [feedback, setFeedback] = useState<{ id: string; message: string; error: boolean } | null>(null)
  const selectedLoad = selected ? streamedLoads?.find((load) => load.external_id === selected.load.external_id) ?? selected.load : null

  function canSubmit(load: LoadView) {
    return connection === 'live' && load.status === 'open'
      && load.seconds_remaining !== 0 && !decisions[load.external_id]
      && !!streamedLoads?.some((item) => item.external_id === load.external_id && item.status === 'open')
  }

  async function decide(load: LoadView, decision: 'bid' | 'decline', bidRate?: string) {
    const id = load.external_id
    if (!canSubmit(load) || lockedOrders.current.has(id)) return
    lockedOrders.current.add(id)
    setDecisions((current) => ({ ...current, [id]: 'submitting' }))
    setFeedback(null)

    try {
      const result = await submitLoadDecision(id, decision, bidRate)
      setDecisions((current) => ({ ...current, [id]: 'sent' }))
      setStream((current) => ({ ...current, loads: current.loads?.map((item) => item.external_id === id ? result.order : item) ?? null }))
      setFeedback({ id, error: false, message: `${id}: ${decision === 'bid' ? 'Bid submitted' : 'Order declined'}.${result.sync_pending ? ' Fleet sync is pending.' : ''}` })
      setSelected(null)
    } catch (cause) {
      const uncertain = !(cause instanceof LoadDecisionError) || cause.uncertain
      if (uncertain) {
        setDecisions((current) => ({ ...current, [id]: 'uncertain' }))
      } else {
        lockedOrders.current.delete(id)
        setDecisions((current) => {
          const next = { ...current }
          delete next[id]
          return next
        })
      }
      setFeedback({ id, error: true, message: `${id}: ${cause instanceof Error ? cause.message : 'Unable to verify the submission.'}` })
    }
  }

  async function checkStatus(id: string) {
    try {
      const response = await getLoad(id)
      if (!response.ok) throw new Error('Unable to check the order status. Please try again.')
      const detail: LoadDetail = await response.json()
      const unresolved = detail.actions.some((action) => action.request_status === 'unknown' || action.request_status === 'submitting')
      if (!unresolved && detail.status === 'open' && detail.actions.length > 0 && detail.actions.every((action) => action.request_status === 'failed')) {
        lockedOrders.current.delete(id)
        setDecisions((current) => {
          const next = { ...current }
          delete next[id]
          return next
        })
      }
      setStream((current) => ({ ...current, loads: current.loads?.map((item) => item.external_id === id ? detail : item) ?? null }))
      setFeedback({ id, error: unresolved, message: unresolved ? `${id}: Submission is still awaiting reconciliation.` : `${id}: Current order status is ${detail.status.replaceAll('_', ' ')}.` })
    } catch (cause) {
      setFeedback({ id, error: true, message: cause instanceof Error ? cause.message : 'Unable to check the order status.' })
    }
  }

  useEffect(() => {
    return subscribeLoads({ order_type: 'open_bid', status: 'open' }, setStream)
  }, [])

  return (
    <PageSection title="Load Board" description="Browse open bid opportunities. Updates arrive automatically; closed orders are available in Bid Logs.">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="text-sm text-base-content/65">Open bids only</p>
        <span role="status" className={`badge badge-soft ${connection === 'live' ? 'badge-success' : 'badge-warning'}`}>
          {connection === 'live' ? 'Live updates' : connection === 'connecting' ? 'Connecting…' : 'Reconnecting…'}
        </span>
      </div>

      {error && (
        <div role="alert" className="alert alert-warning">
          <div>
            <p>{error}</p>
            {loads !== null && <p className="mt-1 text-sm">Showing previous orders. Information may have changed.</p>}
          </div>
        </div>
      )}

      {feedback && (
        <div role={feedback.error ? 'alert' : 'status'} className={`alert ${feedback.error ? 'alert-warning' : 'alert-success'}`}>
          <p>{feedback.message}</p>
          {decisions[feedback.id] === 'uncertain' && <button type="button" className="btn btn-sm btn-outline" onClick={() => void checkStatus(feedback.id)}>Check status</button>}
        </div>
      )}

      <div aria-busy={loads === null}>
        {loads === null && (
          <div role="status" className="flex items-center gap-3 rounded-xl border border-base-300 bg-base-100 p-8">
            <span className="loading loading-spinner text-primary" aria-hidden="true" />
            {connection === 'reconnecting' ? 'Waiting to reconnect for orders…' : 'Loading orders…'}
          </div>
        )}

        {loads?.length === 0 && (
          <EmptyPanel title="No open bids" description="New bid opportunities will appear here automatically as the board updates." />
        )}

        {loads !== null && loads.length > 0 && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-base-content/65">
              <p>{loads.length} {loads.length === 1 ? 'order' : 'orders'}</p>
              {system?.sim_time_utc && <p>Simulation time at update: {new Date(system.sim_time_utc).toLocaleString()}</p>}
            </div>
            <div className="grid items-start gap-5 xl:grid-cols-2 2xl:grid-cols-3">
              {loads.map((load) => (
                <LoadCard
                  key={load.external_id}
                  load={load}
                  disabled={!canSubmit(load)}
                  pending={decisions[load.external_id] === 'submitting'}
                  onAccept={() => setSelected({ load, bid: true })}
                  onDecline={() => void decide(load, 'decline')}
                  onMoreInformation={() => setSelected({ load, bid: false })}
                />
              ))}
            </div>
          </div>
        )}
      </div>
      {selected && selectedLoad && (
        <LoadDetailsPanel
          key={`${selected.load.external_id}-${selected.bid}`}
          load={selectedLoad}
          initialBidOpen={selected.bid}
          canSubmit={canSubmit(selectedLoad)}
          pending={decisions[selectedLoad.external_id] === 'submitting'}
          message={feedback?.id === selectedLoad.external_id ? feedback.message : null}
          onCheckStatus={decisions[selectedLoad.external_id] === 'uncertain' ? () => void checkStatus(selectedLoad.external_id) : undefined}
          onClose={() => setSelected(null)}
          onSubmitBid={(rate) => decide(selectedLoad, 'bid', rate)}
        />
      )}
    </PageSection>
  )
}

import { useEffect, useRef, useState } from 'react'
import { LoadDecisionError, getLoad, submitLoadDecision, subscribeLoads } from '../api/orders'
import type { LiveLoadsState, LoadDetail, LoadView, OrderType } from '../api/orders'
import { getLoadOpportunities } from '../utils/load-board'
import EmptyPanel from '../components/EmptyPanel'
import LoadCard from '../components/LoadCard'
import LoadDetailsPanel from '../components/LoadDetailsPanel'
import PageSection from '../components/PageSection'
import LoadNotification from '../components/LoadNotification'
import type { LoadFeedback } from '../utils/api-feedback'
import { amount } from '../utils/load-format'

const initialState: LiveLoadsState = {
  loads: null,
  system: null,
  connection: 'connecting',
  error: null,
}

export default function LoadBoardPage() {
  const [orderType, setOrderType] = useState<OrderType | 'all'>('all')
  const [{ loads: streamedLoads, system, connection, error }, setStream] = useState(initialState)
  const loads = streamedLoads === null ? null : getLoadOpportunities(streamedLoads, orderType)
  const [selected, setSelected] = useState<{ load: LoadView; bid: boolean } | null>(null)
  const [decisions, setDecisions] = useState<Record<string, 'submitting' | 'sent' | 'uncertain'>>({})
  const lockedOrders = useRef(new Set<string>())
  const [feedback, setFeedback] = useState<LoadFeedback | null>(null)
  const selectedLoad = selected ? streamedLoads?.find((load) => load.external_id === selected.load.external_id) ?? selected.load : null

  function canSubmit(load: LoadView) {
    return connection === 'live' && load.status === 'open'
      && !load.board_missing_at && ['open_bid', 'fixed_rate'].includes(load.order_type)
      && load.seconds_remaining !== 0 && !decisions[load.external_id]
      && !!streamedLoads?.some((item) => item.external_id === load.external_id && item.status === 'open')
  }

  async function decide(load: LoadView, decision: 'accept' | 'bid' | 'decline', bidRate?: string) {
    const id = load.external_id
    if (!canSubmit(load) || lockedOrders.current.has(id)) return
    if ((decision === 'accept' && load.order_type !== 'fixed_rate') || (decision === 'bid' && load.order_type !== 'open_bid')) return
    lockedOrders.current.add(id)
    setDecisions((current) => ({ ...current, [id]: 'submitting' }))
    setFeedback(null)

    try {
      const result = await submitLoadDecision(id, decision, bidRate)
      setDecisions((current) => ({ ...current, [id]: 'sent' }))
      setStream((current) => ({ ...current, loads: current.loads?.map((item) => item.external_id === id ? result.order : item) ?? null }))
      setFeedback({
        id,
        title: decision === 'bid' ? 'Bid submitted' : decision === 'accept' ? 'Offer accepted' : 'Offer declined',
        tone: result.sync_pending ? 'warning' : 'success',
        message: `${decision === 'bid' ? `Your ${amount(bidRate ?? null)} bid was submitted. Track the outcome in Bid Logs; a booking is confirmed only if you win.` : decision === 'accept' ? 'Your acceptance was recorded. Follow this booking in Shipments.' : 'This offer was declined and has been removed from your open opportunities.'}${result.sync_pending ? ' Fleet availability is still updating.' : ''}`,
      })
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
      setFeedback({
        id,
        title: uncertain ? 'Submission not confirmed' : decision === 'bid' ? 'Bid could not be submitted' : decision === 'accept' ? 'Offer could not be accepted' : 'Offer could not be declined',
        tone: uncertain ? 'warning' : 'error',
        message: cause instanceof Error ? cause.message : 'We could not confirm the request. Check the order status before trying again.',
        details: cause instanceof LoadDecisionError ? cause.details : [],
        suggestions: cause instanceof LoadDecisionError ? cause.suggestions : [],
      })
    }
  }

  async function checkStatus(id: string) {
    try {
      const response = await getLoad(id)
      if (!response.ok) throw new Error('Unable to check the order status. Please try again.')
      const detail: LoadDetail = await response.json()
      const unresolved = detail.actions.some((action) => action.request_status === 'unknown' || action.request_status === 'submitting')
      const confirmedFailure = !unresolved && detail.status === 'open' && detail.actions.length > 0 && detail.actions.every((action) => action.request_status === 'failed')
      if (confirmedFailure) {
        lockedOrders.current.delete(id)
        setDecisions((current) => {
          const next = { ...current }
          delete next[id]
          return next
        })
      }
      setStream((current) => ({ ...current, loads: current.loads?.map((item) => item.external_id === id ? detail : item) ?? null }))
      const statusMessages: Record<string, string> = {
        accepted: 'This order is confirmed. Follow its progress in Shipments.',
        in_transit: 'This shipment is on the way. Follow its progress in Shipments.',
        completed: 'This shipment has been delivered.',
        bid_submitted: 'Your bid is recorded and awaiting an outcome. Track it in Bid Logs.',
        bid_lost: 'Your bid was not selected. You can review it in Bid Logs.',
        declined: 'This offer was declined.',
        expired: 'This offer has expired. Choose another open opportunity.',
      }
      if (!unresolved && detail.status !== 'open') setDecisions((current) => ({ ...current, [id]: 'sent' }))
      setFeedback({
        id,
        title: unresolved ? 'Submission still pending' : confirmedFailure ? 'Order available again' : 'Order status updated',
        tone: unresolved || (detail.status === 'open' && !confirmedFailure) ? 'warning' : 'info',
        message: unresolved ? 'The service is still confirming your previous submission. Wait for a confirmed outcome before trying again.' : confirmedFailure ? 'The previous submission failed and this offer is still open. Review its current eligibility before trying again.' : statusMessages[detail.status] ?? (detail.status === 'open' ? 'The offer is still open, but the previous submission has not been verified. Keep checking its status before trying again.' : 'The latest order status has been received. Review its details before continuing.'),
      })
    } catch (cause) {
      setFeedback({ id, title: 'Status check unavailable', tone: 'warning', message: cause instanceof Error ? cause.message : 'We could not read the current order status. Please try checking again.' })
    }
  }

  useEffect(() => {
    return subscribeLoads({ order_type: 'all', status: 'open' }, setStream)
  }, [])

  return (
    <PageSection title="Load Board" description="Browse open fixed-rate and open-bid opportunities. Orders update automatically.">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <label className="flex items-center gap-2 text-sm">
          Order type
          <select className="select select-sm w-44" value={orderType} onChange={(event) => setOrderType(event.target.value as OrderType | 'all')}>
            <option value="all">All order types</option>
            <option value="fixed_rate">Fixed rate</option>
            <option value="open_bid">Open bid</option>
          </select>
        </label>
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

      {feedback && !selected && (
        <div className="fixed inset-x-4 top-24 z-30 mx-auto max-h-[60dvh] max-w-lg overflow-y-auto rounded-xl shadow-xl sm:right-6 sm:left-auto">
          <LoadNotification feedback={feedback} onDismiss={() => setFeedback(null)} onCheckStatus={decisions[feedback.id] === 'uncertain' ? () => void checkStatus(feedback.id) : undefined} />
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
          <EmptyPanel title="No open opportunities" description="New orders matching the selected type will appear here automatically." />
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
          message={null}
          notification={feedback?.id === selectedLoad.external_id ? feedback : undefined}
          onCheckStatus={decisions[selectedLoad.external_id] === 'uncertain' ? () => void checkStatus(selectedLoad.external_id) : undefined}
          onClose={() => setSelected(null)}
          onSubmitBid={(rate) => decide(selectedLoad, 'bid', rate)}
          onAccept={() => decide(selectedLoad, 'accept')}
        />
      )}
    </PageSection>
  )
}

import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { subscribeOverview } from '../api/overview'
import type { LiveOverviewState } from '../api/overview'
import type { ActivityView } from '../api/activity'
import PageSection from '../components/PageSection'
import ActivityDialog from '../components/ActivityDialog'
import { dashboardRoute, dashboardSummary } from '../utils/dashboard'
import { amount, label, quantity, timestamp } from '../utils/load-format'
import { activityColor } from '../utils/activity'
import { readableMessage } from '../utils/api-feedback'

const initialState: LiveOverviewState = {
  overview: null, loads: null, terminals: null, system: null,
  connection: 'connecting', updating: false, error: null, updatedAt: null,
}

function Panel({ title, to, caption, children }: { title: string; to: string; caption: string; children: ReactNode }) {
  return <section className="overflow-hidden rounded-xl border border-base-300 bg-base-100">
    <header className="flex items-start justify-between gap-3 border-b border-base-300 p-5">
      <div><h2 className="font-semibold">{title}</h2><p className="mt-1 text-xs text-base-content/60">{caption}</p></div>
      <Link to={to} className="link link-primary shrink-0 text-xs no-underline hover:underline" aria-label={`View all ${title.toLowerCase()}`}>View all →</Link>
    </header>
    {children}
  </section>
}

function NoData({ loading, children }: { loading: boolean; children: ReactNode }) {
  return <p className="px-5 py-8 text-center text-sm text-base-content/55">{loading ? 'Waiting for operations data…' : children}</p>
}

function count(value: number | null) {
  return value === null ? '—' : value.toLocaleString()
}

export default function DashboardPage() {
  const [state, setState] = useState(initialState)
  const [selectedEvent, setSelectedEvent] = useState<ActivityView | null>(null)
  const refreshRef = useRef<(() => void) | null>(null)
  useEffect(() => {
    const subscription = subscribeOverview(setState)
    refreshRef.current = subscription.refresh
    return () => { refreshRef.current = null; subscription.unsubscribe() }
  }, [])
  const { overview, loads, terminals, system, connection, updating, error, updatedAt } = state
  const summary = dashboardSummary(state)
  const loading = overview === null && loads === null
  const boardDelayed = !!system && ['disconnected', 'reconnecting', 'connecting'].includes(system.connection_status)
  const live = connection === 'live' && !error && !boardDelayed
  const profit = overview?.profit
  const activity = overview?.activity ?? []
  const capacity = [...(terminals ?? [])].sort((left, right) =>
    Number(right.status === 'attention' || right.consistent === false) - Number(left.status === 'attention' || left.consistent === false)
    || left.code.localeCompare(right.code),
  )

  return (
    <PageSection title="Dashboard" description="Your opportunities, capacity, and shipments at a glance.">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span role="status" className={`badge badge-soft ${live ? 'badge-success' : 'badge-warning'}`}>{error ? 'Updates delayed' : boardDelayed ? 'Board connection delayed' : connection === 'reconnecting' ? 'Reconnecting…' : live ? 'Live updates' : 'Connecting…'}</span>
          <p className="text-xs text-base-content/55">{updatedAt ? `Summary refreshed ${timestamp(updatedAt)}` : 'Connecting to operations…'}</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" disabled={updating} onClick={() => refreshRef.current?.()}>{updating ? 'Refreshing…' : error ? 'Retry' : 'Refresh'}</button>
      </div>
      {error && <div role="alert" className="alert alert-warning text-sm"><div><p>{error}</p><p className="mt-1 text-xs">{overview || loads ? 'Showing the latest available data. ' : ''}Updates retry automatically.</p></div></div>}
      {boardDelayed && !error && <p role="status" className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm">The dispatcher is reconnecting to the board. Showing the last synced operations data. Last board sync: {timestamp(system?.last_sync_at ?? null)}.</p>}
      <div aria-busy={loading} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { title: 'Live opportunities', value: summary.openCount, to: '/loads', note: 'Open fixed-rate & open-bid orders' },
          { title: 'Available trucks', value: summary.availableUnits, to: '/terminals', note: summary.totalUnits === null ? 'Waiting for terminal capacity' : `Across ${count(summary.totalUnits)} trucks in the fleet` },
          { title: 'Pending bids', value: summary.pendingCount, to: '/bids', note: 'Submitted bids awaiting an outcome' },
          { title: 'Active shipments', value: summary.activeCount, to: '/shipments', note: 'Confirmed bookings & shipments in transit' },
        ].map((item) => <Link key={item.to} to={item.to} className="group rounded-xl border border-base-300 bg-base-100 p-5 transition-colors hover:border-primary/40 focus-visible:outline-2 focus-visible:outline-primary">
          <div className="flex items-center justify-between gap-2"><h2 className="text-sm text-base-content/65">{item.title}</h2><span aria-hidden="true" className="text-primary/50 group-hover:text-primary">↗</span></div>
          <p className="my-3 text-3xl font-bold tabular-nums text-primary">{count(item.value)}</p>
          <p className="text-xs text-base-content/55">{item.note}</p>
        </Link>)}
      </div>

      <section aria-labelledby="dashboard-profit-title" className="rounded-xl border border-primary/20 bg-primary/5 p-5">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2"><h2 id="dashboard-profit-title" className="font-semibold">Estimated profit</h2><p className="text-xs text-base-content/55">Saved booking estimates · USD · Not realized earnings</p></div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div><p className="text-xs text-base-content/60">Confirmed bookings</p><p className={`mt-2 text-2xl font-bold tabular-nums ${profit && Number(profit.confirmed_estimated_profit) < 0 ? 'text-error' : 'text-primary'}`}>{amount(profit?.confirmed_estimated_profit ?? null)}</p><p className="mt-1 text-xs text-base-content/60">{profit ? `${profit.confirmed_estimated_count} known estimates · ${profit.confirmed_unknown_count} unavailable` : 'Waiting for saved booking estimates'}</p></div>
          <div className="border-t border-primary/15 pt-4 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-5"><p className="text-xs text-base-content/60">Pending bids · Conditional</p><p className={`mt-2 text-2xl font-bold tabular-nums ${profit && Number(profit.conditional_pending_bid_profit) < 0 ? 'text-error' : 'text-base-content'}`}>{amount(profit?.conditional_pending_bid_profit ?? null)}</p><p className="mt-1 text-xs text-base-content/60">{profit ? `${profit.pending_estimated_count} known estimates · ${profit.pending_unknown_count} unavailable` : 'Waiting for pending bid estimates'}. Only applies if the bids win.</p></div>
        </div>
      </section>

      <div className="grid items-start gap-5 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Open opportunities" to="/loads" caption="Up to five offers · Soonest expiry first">
          {summary.opportunities.length ? <ul className="divide-y divide-base-200">{summary.opportunities.map((load) => <li key={load.external_id} className="space-y-2 p-5">
            <div className="flex items-center justify-between gap-3"><span className="truncate text-xs text-base-content/55" title={load.external_id}>{load.external_id}</span><span className="badge badge-sm badge-soft badge-primary shrink-0">{load.order_type === 'fixed_rate' ? 'Fixed rate' : 'Open bid'}</span></div>
            <p className="text-sm font-medium">{dashboardRoute(load)}</p>
            <div className="flex flex-wrap justify-between gap-2 text-xs"><span className="text-base-content/60">{quantity(load.distance_miles, 'mi')} · {quantity(load.weight_lbs, 'lbs')}</span><span>{load.order_type === 'fixed_rate' ? `Offered ${amount(load.offered_rate)}` : `Board cost ${amount(load.estimated_total_cost)}`}</span></div>
            <p className="text-xs text-base-content/55">Expires {timestamp(load.expires_at)}</p>
          </li>)}</ul> : <NoData loading={loading}>No open opportunities. New orders will appear automatically.</NoData>}
        </Panel>
        <Panel title="Terminal capacity" to="/terminals" caption={summary.attentionCount ? `${summary.attentionCount} hubs need attention · Current roster counts` : 'Current available trucks by hub'}>
          {capacity.length ? <ul className="max-h-[30rem] divide-y divide-base-200 overflow-y-auto">{capacity.map((terminal) => {
            const needsAttention = terminal.status === 'attention' || terminal.consistent === false
            const known = terminal.total_units !== null && terminal.available_units !== null && terminal.total_units > 0 && terminal.available_units <= terminal.total_units
            return <li key={terminal.terminal_id} className="space-y-2 p-5">
              <div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold">{terminal.code} <span className="font-normal text-base-content/60">· {terminal.city}</span></p><p className="mt-1 text-xs text-base-content/55">{count(terminal.assigned_units)} assigned / {count(terminal.total_units)} total</p></div><div className="text-right"><p className="text-lg font-bold tabular-nums text-primary">{count(terminal.available_units)} <span className="text-xs font-normal text-base-content/55">available</span></p>{needsAttention && <Link to="/terminals" className="text-xs text-warning underline">Review capacity</Link>}</div></div>
              {known && <progress className={`progress h-1.5 w-full ${needsAttention ? 'progress-warning' : 'progress-primary'}`} value={terminal.available_units ?? 0} max={terminal.total_units ?? 1} aria-label={`${terminal.code} available trucks`} />}
            </li>
          })}</ul> : <NoData loading={terminals === null}>No terminal capacity has been synced yet.</NoData>}
        </Panel>
        <Panel title="Active shipments" to="/shipments" caption="Up to five confirmed shipments · Soonest delivery first">
          {summary.shipments.length ? <ul className="divide-y divide-base-200">{summary.shipments.map((shipment) => {
            const overdue = shipment.status === 'in_transit' && !!system?.sim_time_utc && !!shipment.delivery_at && Date.parse(shipment.delivery_at) < Date.parse(system.sim_time_utc)
            return <li key={shipment.external_id} className="space-y-2 p-5"><div className="flex items-center justify-between gap-3"><span className="truncate text-xs text-base-content/55" title={shipment.external_id}>{shipment.external_id}</span><span className={`badge badge-sm badge-soft ${overdue ? 'badge-warning' : shipment.status === 'in_transit' ? 'badge-info' : 'badge-success'}`}>{overdue ? 'Delivery overdue' : shipment.status === 'in_transit' ? 'In transit' : 'Booked'}</span></div><p className="text-sm font-medium">{dashboardRoute(shipment)}</p><p className="text-xs text-base-content/60">Delivery {timestamp(shipment.delivery_at)}</p><p className="text-xs text-base-content/55">Assigned truck: {shipment.board_assigned_unit_id ?? 'Not yet synced'}</p></li>
          })}</ul> : <NoData loading={loading}>No active shipments. Accepted bookings will appear here.</NoData>}
        </Panel>
        <Panel title="Pending bids" to="/bids" caption="Up to five pending bids · Soonest decision first">
          {summary.pendingBids.length ? <ul className="divide-y divide-base-200">{summary.pendingBids.map((order) => {
            const bid = overview?.bids.find((item) => item.order.external_id === order.external_id)
            return <li key={order.external_id} className="space-y-2 p-5"><div className="flex items-center justify-between gap-3"><span className="truncate text-xs text-base-content/55" title={order.external_id}>{order.external_id}</span><span className="badge badge-sm badge-soft badge-warning">Awaiting result</span></div><p className="text-sm font-medium">{dashboardRoute(order)}</p><div className="flex flex-wrap items-center justify-between gap-2 text-xs"><span className="text-base-content/60">Decision {timestamp(order.bid_decision_at)}</span><span className="font-semibold">{bid?.bid_rate ? `Bid ${amount(bid.bid_rate)}` : 'Bid amount not loaded'}</span></div></li>
          })}</ul> : <NoData loading={loading}>No pending bids. Submitted bids will appear here.</NoData>}
        </Panel>
      </div>
      <Panel title="Recent activity" to="/activity" caption="The five latest decisions, results, and sync events">
        {activity.length ? <ul className="divide-y divide-base-200">{activity.map((event) => <li key={event.event_id}><button type="button" className="flex w-full flex-wrap items-start gap-3 p-5 text-left transition-colors hover:bg-base-200/50" onClick={() => setSelectedEvent(event)} aria-haspopup="dialog">
          <span className={`badge badge-sm badge-soft shrink-0 ${activityColor(event.event_type)}`}>{label(event.event_type.replaceAll('.', ' '))}</span>
          <div className="min-w-0 flex-1"><p className="line-clamp-2 break-words text-sm">{readableMessage(event.message)}</p><p className="mt-1 break-all text-xs text-base-content/50">{event.external_id ?? 'System event'}</p></div>
          <time dateTime={event.occurred_at_wall} className="text-xs text-base-content/55">{timestamp(event.occurred_at_wall)}</time>
        </button></li>)}</ul> : <NoData loading={overview === null}>No activity yet. Updates will appear as operations begin.</NoData>}
      </Panel>
      {selectedEvent && <ActivityDialog event={activity.find((event) => event.event_id === selectedEvent.event_id) ?? selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </PageSection>
  )
}

import { useEffect, useRef, useState } from 'react'
import { subscribeBidLogs } from '../api/bid-log-stream'
import type { LiveBidLogsState } from '../api/bid-log-stream'
import type { BidView } from '../api/bids'
import EmptyPanel from '../components/EmptyPanel'
import PageSection from '../components/PageSection'
import BidLogDialog from '../components/BidLogDialog'
import { BID_LOG_PAGE_SIZE, filterBidLogs, getBidDate, getBidLogPage, sortBidLogs } from '../utils/bid-logs'
import type { BidDateField, BidSortField, BidStatusFilter, SortDirection } from '../utils/bid-logs'

const columns: Array<{ field: BidSortField; label: string }> = [
  { field: 'order', label: 'Order' },
  { field: 'status', label: 'Order status' },
  { field: 'route', label: 'Route' },
  { field: 'amount', label: 'Bid amount' },
  { field: 'outcome', label: 'Outcome' },
  { field: 'request', label: 'Submission status' },
  { field: 'decision', label: 'Decision time' },
]

const tableColumns = columns.filter((column) => column.field !== 'outcome' && column.field !== 'request')

const dateOptions: Array<{ value: BidDateField; label: string }> = [
  { value: 'created', label: 'Created' },
  { value: 'synced', label: 'Last synced' },
  { value: 'decision', label: 'Decision' },
  { value: 'pickup', label: 'Pickup' },
  { value: 'delivery', label: 'Delivery' },
  { value: 'expires', label: 'Offer expires' },
]

const statusOptions: Array<{ value: BidStatusFilter; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'declined', label: 'Declined' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'expired', label: 'Expired' },
  { value: 'pending', label: 'Pending' },
  { value: 'lost', label: 'Lost' },
  { value: 'in_transit', label: 'In transit' },
  { value: 'completed', label: 'Completed' },
  { value: 'unknown', label: 'Unknown outcome' },
]

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export default function BidLogsPage() {
  const [{ bids, connection, updating, error }, setStream] = useState<LiveBidLogsState>({
    bids: null,
    connection: 'connecting',
    updating: false,
    error: null,
  })
  const [sortField, setSortField] = useState<BidSortField>('decision')
  const [direction, setDirection] = useState<SortDirection>('desc')
  const [dateField, setDateField] = useState<BidDateField>('decision')
  const [statusFilter, setStatusFilter] = useState<BidStatusFilter>('all')
  const statusFilterRef = useRef<BidStatusFilter>('all')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<BidView | null>(null)
  const selectedBid = selected ? bids?.find((bid) => bid.order.external_id === selected.order.external_id) ?? selected : null

  useEffect(() => {
    return subscribeBidLogs((state) => {
      setStream(state)
      if (state.bids !== null) {
        const totalPages = Math.max(1, Math.ceil(filterBidLogs(state.bids, statusFilterRef.current).length / BID_LOG_PAGE_SIZE))
        setPage((current) => Math.min(current, totalPages))
      }
    })
  }, [])

  function changeSort(field: BidSortField) {
    setDirection(field === sortField && direction === 'asc' ? 'desc' : 'asc')
    setSortField(field)
    setPage(1)
  }

  const filteredBids = filterBidLogs(bids ?? [], statusFilter)
  const sortedBids = sortBidLogs(filteredBids, sortField, direction)
  const pagination = getBidLogPage(sortedBids, page)
  const sortingByDate = dateOptions.some((option) => option.value === sortField)
  const dateLabel = dateOptions.find((option) => option.value === dateField)?.label ?? 'Decision'
  const displayedColumns = tableColumns.map((column) => column.field === 'decision'
    ? { field: dateField, label: `${dateLabel} date` }
    : column)

  return (
    <PageSection title="Bid Logs" description="Review non-open bid orders and their outcomes. Logs update automatically.">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p role="status" className="text-sm text-base-content/65">
          {bids === null ? 'Loading bid logs…' : `${filteredBids.length} of ${bids.length} records`}
        </p>
        <span role="status" className={`badge badge-soft ${connection === 'live' && !error ? 'badge-success' : 'badge-warning'}`}>
          {connection === 'connecting' ? 'Connecting…' : connection === 'reconnecting' ? 'Reconnecting…' : error ? 'Updates delayed' : updating ? 'Updating…' : 'Live updates'}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          Status
          <select className="select select-sm w-40" value={statusFilter} onChange={(event) => {
            const value = event.target.value as BidStatusFilter
            statusFilterRef.current = value
            setStatusFilter(value)
            setPage(1)
          }}>
            {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          Sort by
          <select className="select select-sm w-40" value={sortingByDate ? 'date' : sortField} onChange={(event) => {
            setSortField(event.target.value === 'date' ? dateField : event.target.value as BidSortField)
            setPage(1)
          }}>
            <option value="date">Date</option>
            {columns.filter((column) => column.field !== 'decision').map((column) => <option key={column.field} value={column.field}>{column.label}</option>)}
          </select>
        </label>
        {sortingByDate && (
          <label className="flex items-center gap-2 text-sm">
            Date
            <select className="select select-sm w-44" value={dateField} onChange={(event) => {
              const value = event.target.value as BidDateField
              setDateField(value)
              setSortField(value)
              setPage(1)
            }}>
              {dateOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              <option value="received" disabled>Received (unavailable)</option>
            </select>
          </label>
        )}
        <label className="flex items-center gap-2 text-sm">
          Order
          <select className="select select-sm w-36" value={direction} onChange={(event) => {
            setDirection(event.target.value as SortDirection)
            setPage(1)
          }}>
            <option value="asc">{sortingByDate ? 'Oldest first' : 'Ascending'}</option>
            <option value="desc">{sortingByDate ? 'Newest first' : 'Descending'}</option>
          </select>
        </label>
        <span className="text-xs text-base-content/60">20 per page</span>
      </div>

      {error && (
        <div role="alert" className="alert alert-warning">
          <div>
            <p>{error}</p>
            <p className="mt-1 text-sm">{bids !== null ? 'Showing previous results. ' : ''}Updates will resume automatically when the connection and service recover.</p>
          </div>
        </div>
      )}

      <div aria-busy={bids === null || updating}>
        {bids === null && (
          <div className="flex items-center gap-3 rounded-xl border border-base-300 bg-base-100 p-8">
            <span className="loading loading-spinner text-primary" aria-hidden="true" />
            {connection === 'reconnecting' ? 'Waiting to reconnect for bid records…' : 'Loading bid records…'}
          </div>
        )}

        {bids?.length === 0 && <EmptyPanel title="No bid history yet" description="Expired, accepted, declined, and other non-open orders will appear here." />}

        {bids !== null && bids.length > 0 && filteredBids.length === 0 && <EmptyPanel title="No matching records" description="Choose another status to see more bid logs." />}

        {bids !== null && filteredBids.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-base-300 bg-base-100">
            <div className="overflow-x-auto">
            <table className="table table-sm">
              <caption className="sr-only">Non-open orders and latest bid records. Unknown sort values appear last.</caption>
              <thead>
                <tr>
                  {displayedColumns.map((column) => (
                    <th key={column.field} scope="col" aria-sort={sortField === column.field ? direction === 'asc' ? 'ascending' : 'descending' : 'none'}>
                      <button type="button" className="flex items-center gap-2 rounded p-1 text-left hover:text-primary focus-visible:outline-2 focus-visible:outline-primary" onClick={() => changeSort(column.field)}>
                        {column.label}
                        <span aria-hidden="true">{sortField === column.field ? direction === 'asc' ? '↑' : '↓' : '↕'}</span>
                      </button>
                    </th>
                  ))}
                  <th scope="col" className="text-right">Details</th>
                </tr>
              </thead>
              <tbody>
                {pagination.records.map((bid) => {
                  const date = getBidDate(bid, dateField)
                  return (
                  <tr key={bid.action_id ?? bid.order.external_id} className="hover:bg-base-200/60">
                    <th scope="row" className="font-normal">
                      <p className="font-semibold text-primary">{bid.order.external_id}</p>
                    </th>
                    <td>
                      <span className="badge badge-sm badge-soft badge-primary capitalize whitespace-nowrap">{bid.order.status.replaceAll('_', ' ')}</span>
                      <p className={`mt-1 text-xs capitalize ${bid.outcome === 'rejected' ? 'text-error' : 'text-base-content/60'}`}>{bid.outcome.replaceAll('_', ' ')}</p>
                    </td>
                    <td className="whitespace-nowrap">
                      {bid.order.origin_terminal_code ?? 'Unknown'} → {bid.order.destination_terminal_code ?? 'Unknown'}
                    </td>
                    <td className="whitespace-nowrap font-semibold tabular-nums">
                      {bid.bid_rate === null ? '—' : currency.format(Number(bid.bid_rate))}
                    </td>
                    <td className="whitespace-nowrap text-xs">
                      {date && !Number.isNaN(Date.parse(date)) ? (
                        <><p>{new Date(date).toLocaleDateString()}</p><p className="mt-1 text-base-content/60">{new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p></>
                      ) : '—'}
                    </td>
                    <td className="text-right"><button type="button" className="btn btn-ghost btn-xs whitespace-nowrap text-primary" aria-haspopup="dialog" aria-label={`More information about ${bid.order.external_id}`} onClick={() => setSelected(bid)}>More information</button></td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-base-300 px-4 py-3">
              <p className="text-xs text-base-content/60" role="status">Showing {pagination.first}–{pagination.last} of {filteredBids.length}</p>
              <nav aria-label="Bid logs pagination" className="flex items-center gap-3">
                <span className="text-xs text-base-content/60">Page {pagination.page} of {pagination.totalPages}</span>
                <div className="join">
                  <button type="button" className="btn btn-sm join-item" aria-label="First page" disabled={pagination.page === 1} onClick={() => setPage(1)}>{'<<'}</button>
                  <button type="button" className="btn btn-sm join-item" aria-label="Previous page" disabled={pagination.page === 1} onClick={() => setPage(pagination.page - 1)}>{'<'}</button>
                  <span className="btn btn-sm join-item pointer-events-none tabular-nums" aria-current="page" aria-label={`Page ${pagination.page}`}>{pagination.page}</span>
                  <button type="button" className="btn btn-sm join-item" aria-label="Next page" disabled={pagination.page === pagination.totalPages} onClick={() => setPage(pagination.page + 1)}>{'>'}</button>
                  <button type="button" className="btn btn-sm join-item" aria-label="Last page" disabled={pagination.page === pagination.totalPages} onClick={() => setPage(pagination.totalPages)}>{'>>'}</button>
                </div>
              </nav>
            </div>
          </div>
        )}
      </div>
      {selectedBid && <BidLogDialog bid={selectedBid} onClose={() => setSelected(null)} />}
    </PageSection>
  )
}

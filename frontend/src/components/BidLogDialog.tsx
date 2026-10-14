import { useEffect, useRef } from 'react'
import type { BidView } from '../api/types'
import { amount, label, timestamp } from '../utils/load-format'
import LoadInformation from './LoadInformation'
import Field from './LoadField'

export default function BidLogDialog({ bid, onClose }: { bid: BidView; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog?.showModal()
    return () => {
      dialog?.close()
      document.body.style.overflow = previousOverflow
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="bid-log-title"
      className="m-auto max-h-[90dvh] w-[calc(100%_-_2rem)] max-w-3xl overflow-hidden rounded-2xl border border-base-300 bg-base-100 p-0 text-base-content shadow-2xl backdrop:bg-black/40"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect()
        if (event.target === event.currentTarget && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) onClose()
      }}
    >
      <div className="flex max-h-[90dvh] flex-col">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-base-300 p-6">
          <div className="min-w-0">
            <p className="text-xs text-base-content/60">Bid log information</p>
            <h2 id="bid-log-title" className="mt-1 break-all text-xl font-bold text-primary">{bid.order.external_id}</h2>
          </div>
          <button type="button" className="btn btn-ghost btn-circle btn-sm shrink-0" onClick={onClose} aria-label="Close bid log information">✕</button>
        </header>
        <div className="min-h-0 space-y-7 overflow-y-auto p-6">
          <div className="flex flex-wrap gap-2">
            <span className="badge badge-soft badge-primary capitalize">{label(bid.order.status)}</span>
            <span className="badge badge-outline capitalize">{label(bid.outcome)}</span>
          </div>
          <dl className="grid grid-cols-2 gap-5 rounded-xl bg-base-200 p-4 sm:grid-cols-3">
            <Field title="Bid amount">{amount(bid.bid_rate)}</Field>
            <Field title="Submission status">{bid.request_status ? label(bid.request_status) : 'No submission recorded'}</Field>
            <Field title="Decision time">{timestamp(bid.decision_at)}</Field>
            <Field title="Action ID">{bid.action_id}</Field>
          </dl>
          <LoadInformation load={bid.order} />
        </div>
        <footer className="flex shrink-0 justify-end border-t border-base-300 p-4">
          <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>Close</button>
        </footer>
      </div>
    </dialog>
  )
}

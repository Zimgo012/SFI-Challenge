import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { LoadView } from '../api/orders'
import { label } from '../utils/load-format'
import { isValidBidAmount } from '../utils/bid-amount'
import LoadInformation from './LoadInformation'

type LoadDetailsPanelProps = {
  load: LoadView
  initialBidOpen: boolean
  canSubmit: boolean
  pending: boolean
  message: string | null
  onCheckStatus?: () => void
  onClose: () => void
  onSubmitBid: (bidRate: string) => Promise<void>
}

export default function LoadDetailsPanel({ load, initialBidOpen, canSubmit, pending, message, onCheckStatus, onClose, onSubmitBid }: LoadDetailsPanelProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const bidInputRef = useRef<HTMLInputElement>(null)
  const [bidOpen, setBidOpen] = useState(initialBidOpen)
  const [bidRate, setBidRate] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

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

  useEffect(() => {
    if (bidOpen) bidInputRef.current?.focus()
  }, [bidOpen])

  function submitBid(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit || pending) return
    if (!isValidBidAmount(bidRate.trim())) {
      setValidationError('Enter a positive bid amount with up to 18 digits and 6 decimal places.')
      return
    }
    setValidationError(null)
    void onSubmitBid(bidRate.trim())
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="load-panel-title"
      className="load-details-panel fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-full max-w-lg border-0 bg-base-100 p-0 text-base-content shadow-2xl backdrop:bg-black/40"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect()
        if (event.target === event.currentTarget && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) onClose()
      }}
    >
      <div className="flex h-full flex-col">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-base-300 p-6">
          <div className="min-w-0">
            <p className="text-xs text-base-content/60">Order information</p>
            <h2 id="load-panel-title" className="mt-1 break-all text-lg font-bold text-primary">{load.external_id}</h2>
          </div>
          <button type="button" className="btn btn-ghost btn-circle btn-sm shrink-0" aria-label="Close order information" onClick={onClose}>✕</button>
        </header>
        <div className="min-h-0 flex-1 space-y-7 overflow-y-auto p-6">
          <div className="flex flex-wrap gap-2">
            <span className="badge badge-outline badge-primary">{label(load.order_type)}</span>
            <span className="badge badge-soft capitalize">{label(load.status)}</span>
          </div>

          {message && <div role="alert" className="alert alert-warning"><p>{message}</p>{onCheckStatus && <button type="button" className="btn btn-sm btn-outline" onClick={onCheckStatus}>Check status</button>}</div>}

          {bidOpen ? (
            <form className="space-y-4 rounded-xl border border-primary/25 bg-primary/5 p-4" onSubmit={submitBid}>
              <div>
                <h3 className="font-semibold">Place your bid</h3>
                <p className="mt-1 text-sm text-base-content/65">Accept this opportunity by submitting a bid. A booking is confirmed only if your bid wins.</p>
              </div>
              <label htmlFor="load-bid-amount" className="block text-sm font-medium">Bid amount (USD)</label>
              <input ref={bidInputRef} id="load-bid-amount" className="input input-bordered w-full" type="text" inputMode="decimal" placeholder="2100.25" required value={bidRate} disabled={!canSubmit || pending} aria-invalid={!!validationError} aria-describedby={validationError ? 'load-bid-error' : undefined} onChange={(event) => setBidRate(event.target.value)} />
              {validationError && <p id="load-bid-error" role="alert" className="text-sm text-error">{validationError}</p>}
              <button type="submit" className="btn btn-primary w-full" disabled={!canSubmit || pending}>
                {pending && <span className="loading loading-spinner loading-sm" aria-hidden="true" />}
                {pending ? 'Submitting bid…' : 'Submit bid'}
              </button>
              {!canSubmit && !pending && <p className="text-sm text-base-content/65">This order is unavailable for submission. Check the latest order status before continuing.</p>}
            </form>
          ) : (
            <button type="button" className="btn btn-primary w-full" disabled={!canSubmit} onClick={() => setBidOpen(true)}>Accept &amp; place a bid</button>
          )}

          <LoadInformation load={load} />
        </div>
      </div>
    </dialog>
  )
}

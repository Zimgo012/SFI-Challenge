import { useEffect, useRef } from 'react'
import type { LoadView } from '../api/orders'
import { label } from '../utils/load-format'
import ProfitMarginAnalyzer from './ProfitMarginAnalyzer'
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
  onAccept: () => Promise<void>
}

export default function LoadDetailsPanel({ load, initialBidOpen, canSubmit, pending, message, onCheckStatus, onClose, onSubmitBid, onAccept }: LoadDetailsPanelProps) {
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

  const isOpenBid = load.order_type === 'open_bid'

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="load-panel-title"
      className={`load-details-panel fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-full border-0 bg-base-100 p-0 text-base-content shadow-2xl backdrop:bg-black/40 ${isOpenBid ? 'max-w-5xl' : 'max-w-lg'}`}
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect()
        if (event.target === event.currentTarget && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) onClose()
      }}
    >
      <div className="flex h-full flex-col">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-base-300 px-5 py-4">
          <div className="min-w-0">
            <h2 id="load-panel-title" className="text-lg font-bold text-primary">{isOpenBid ? 'Profit margin analyzer' : 'Order information'}</h2>
            <p className="mt-1 truncate text-xs text-base-content/60" title={load.external_id}>{load.external_id} · {label(load.status)}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-circle btn-sm shrink-0" aria-label="Close order information" onClick={onClose}>✕</button>
        </header>
        {isOpenBid ? <>
          {message && <div role="alert" className="alert alert-warning shrink-0 rounded-none"><p>{message}</p>{onCheckStatus && <button type="button" className="btn btn-sm btn-outline" onClick={onCheckStatus}>Check status</button>}</div>}
          <ProfitMarginAnalyzer load={load} canSubmit={canSubmit} pending={pending} onSubmitBid={onSubmitBid} orderInformation={<LoadInformation load={load} />} initialTab={initialBidOpen ? 'economics' : 'order'} />
        </> : <div className="min-h-0 flex-1 space-y-7 overflow-y-auto p-6">
          <div className="flex flex-wrap gap-2">
            <span className="badge badge-outline badge-primary">{label(load.order_type)}</span>
            <span className="badge badge-soft capitalize">{label(load.status)}</span>
          </div>

          {message && <div role="alert" className="alert alert-warning"><p>{message}</p>{onCheckStatus && <button type="button" className="btn btn-sm btn-outline" onClick={onCheckStatus}>Check status</button>}</div>}

          <button type="button" className="btn btn-primary w-full" disabled={!canSubmit || pending} onClick={() => void onAccept()}>{pending ? 'Accepting…' : 'Accept fixed-rate offer'}</button>

          <LoadInformation load={load} />
        </div>}
      </div>
    </dialog>
  )
}

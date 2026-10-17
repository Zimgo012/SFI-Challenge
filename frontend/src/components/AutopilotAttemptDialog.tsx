import { useEffect, useRef } from 'react'
import type { AutopilotAttempt } from '../api/types'
import { autopilotReason, autopilotStatusColor } from '../utils/autopilot'
import { amount, label, quantity, timestamp } from '../utils/load-format'
import Field from './LoadField'

export default function AutopilotAttemptDialog({ attempt, onClose }: { attempt: AutopilotAttempt; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    ref.current?.showModal()
    const dialog = ref.current
    return () => { dialog?.close(); document.body.style.overflow = overflow }
  }, [])
  const evaluation = attempt.evaluation_snapshot
  const economics = evaluation.economics
  return <dialog ref={ref} aria-labelledby="autopilot-attempt-title" className="m-auto max-h-[90dvh] w-[calc(100%_-_2rem)] max-w-3xl overflow-hidden rounded-xl border border-base-300 bg-base-100 p-0 text-base-content shadow-2xl backdrop:bg-black/40" onCancel={event => { event.preventDefault(); onClose() }} onClick={event => {
    const box = event.currentTarget.getBoundingClientRect()
    if (event.target === event.currentTarget && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) onClose()
  }}><div className="flex max-h-[90dvh] flex-col">
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-base-300 p-5"><h2 id="autopilot-attempt-title" className="min-w-0 truncate font-semibold">{attempt.external_id} · Autopilot decision</h2><button type="button" className="btn btn-ghost btn-circle btn-sm" aria-label="Close autopilot decision" onClick={onClose}>✕</button></header>
    <div className="min-h-0 space-y-5 overflow-y-auto p-5">
      <div className="flex flex-wrap gap-2"><span className={`badge badge-soft ${attempt.order_type === 'fixed_rate' ? 'badge-success' : 'badge-info'}`}>{label(attempt.order_type)}</span><span className={`badge badge-soft ${autopilotStatusColor(attempt.decision ?? '')}`}>{attempt.decision ?? 'Evaluating'}</span><span className={`badge badge-soft ${autopilotStatusColor(attempt.status)}`}>{label(attempt.status)}</span></div>
      {attempt.message && <p className="text-sm">{attempt.message}</p>}
      {attempt.reason_codes.length > 0 && <ul className="space-y-2 text-xs text-warning">{attempt.reason_codes.map(code => <li key={code}>{autopilotReason(code)}</li>)}</ul>}
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Field title="Bid / offer">{amount(attempt.bid_rate ?? economics?.payout ?? null)}</Field><Field title="Estimated total cost">{amount(economics?.total_cost ?? null)}</Field><Field title="Estimated profit">{amount(economics?.gross_profit ?? null)}</Field><Field title="Margin">{quantity(economics?.margin_pct ?? null, '%')}</Field><Field title="Empty miles">{quantity(evaluation.deadhead_miles ?? null, 'mi')}</Field><Field title="Selected unit">{attempt.candidate_unit_id}</Field>
        <Field title="Evaluated">{timestamp(attempt.decided_at_wall)}</Field><Field title="Finished">{timestamp(attempt.finished_at_wall)}</Field><Field title="Action ID">{attempt.action_id}</Field>
        <Field title="Allocation plan">{attempt.allocation_plan_id}</Field>
      </dl>
      {evaluation.checks && <section><h3 className="text-sm font-semibold">Dispatch checks</h3><dl className="mt-3 grid grid-cols-2 gap-2 text-xs">{Object.entries(evaluation.checks).map(([check, passed]) => <div key={check} className="flex justify-between gap-2"><dt>{label(check).replace(/ passed$/, '')}</dt><dd className={evaluation.skipped_checks?.includes(check) ? 'text-base-content/50' : passed ? 'text-success' : 'text-error'}>{evaluation.skipped_checks?.includes(check) ? 'Skipped' : passed ? 'Passed' : 'Blocked'}</dd></div>)}</dl></section>}
      {evaluation.primary_rejection && <p className="text-xs text-warning">{evaluation.primary_rejection.message}</p>}
      <details className="rounded-lg border border-base-300 p-3"><summary className="cursor-pointer text-xs font-semibold">Model request & response</summary><pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words text-[11px]">{Object.keys(attempt.model_snapshot).length ? JSON.stringify(attempt.model_snapshot, null, 2) : attempt.order_type === 'fixed_rate' ? 'Fixed-rate offers use deterministic economics without a model request.' : 'No model response was recorded. Check the decision reasons.'}</pre></details>
      <details className="rounded-lg border border-base-300 p-3"><summary className="cursor-pointer text-xs font-semibold">Full evaluation</summary><pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words text-[11px]">{JSON.stringify(evaluation, null, 2)}</pre></details>
      <p className="text-[11px] text-base-content/55">A submitted bid is awaiting its award outcome. Follow Bid Logs and Shipments for the result. All profit figures here are estimates.</p>
    </div>
  </div></dialog>
}

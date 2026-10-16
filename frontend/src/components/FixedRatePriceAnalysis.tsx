import type { LoadView, OrderRecommendations } from '../api/types'
import type { FixedPriceAnalysis } from '../utils/price-analysis'
import { timestamp } from '../utils/load-format'
import PriceAnalysisChart from './PriceAnalysisChart'
import PriceAnalysisMetrics from './PriceAnalysisMetrics'

type Props = {
  load: LoadView
  report?: OrderRecommendations
  loading?: boolean
  error?: string
  onRefresh?: () => void
}

export default function FixedRatePriceAnalysis({ load, report, loading = false, error, onRefresh }: Props) {
  const current = report?.external_id === load.external_id ? report : null
  const evaluation = current?.dispatch_evaluation
  const economics = current?.selected?.economics ?? evaluation?.economics ?? null
  const analysis: FixedPriceAnalysis = {
    order_type: 'fixed_rate', economics,
    offered_rate: economics?.payout ?? load.offered_rate,
    distance_miles: load.distance_miles,
  }

  return <section aria-label="Price analysis" className="space-y-3" aria-busy={loading}>
    <div>
      <h3 className="text-base font-semibold">Price analysis</h3>
      <p className="mt-1 text-[11px] text-base-content/60">Review the fixed offer against backend costs and profit requirements.</p>
    </div>
    {loading && <p role="status" className="flex items-center gap-2 text-xs text-base-content/60"><span className="loading loading-spinner loading-xs" />Updating fixed-rate analysis…</p>}
    {error && <p role="alert" className="text-xs text-error">{error}</p>}
    {error && onRefresh && <button type="button" className="btn btn-ghost btn-xs" disabled={loading} onClick={onRefresh}>Retry analysis</button>}
    {current && <>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="badge badge-sm badge-soft badge-info">Fixed-rate economics</span>
        <span className="text-base-content/55">{timestamp(current.evaluated_at_sim)} · simulation time</span>
      </div>
      <PriceAnalysisChart result={analysis} bid={analysis.offered_rate} />
      <PriceAnalysisMetrics result={analysis} />
      {evaluation?.primary_rejection?.message && <p className="text-xs text-warning">{evaluation.primary_rejection.message}</p>}
      {economics?.missing_inputs.map((input, index) => <p key={index} className="text-xs text-warning">{input.message}</p>)}
    </>}
    <p className="text-[10px] text-base-content/50">Uses the board’s offered payout and the backend cost preview. Model price advice is available for open bids only.</p>
  </section>
}

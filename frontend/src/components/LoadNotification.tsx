import type { LoadFeedback } from '../utils/api-feedback'

export default function LoadNotification({ feedback, onCheckStatus, onDismiss }: { feedback: LoadFeedback; onCheckStatus?: () => void; onDismiss?: () => void }) {
  return <div role={feedback.tone === 'success' || feedback.tone === 'info' ? 'status' : 'alert'} className={`alert items-start ${feedback.tone === 'success' ? 'alert-success' : feedback.tone === 'error' ? 'alert-error' : feedback.tone === 'info' ? 'alert-info' : 'alert-warning'}`}>
    <div className="min-w-0 space-y-2 text-sm">
      <p className="font-semibold">{feedback.title}</p>
      <p className="break-words leading-relaxed">{feedback.message}</p>
      {!!feedback.details?.length && <ul className="list-disc space-y-1 pl-4">{feedback.details.map((detail) => <li key={detail} className="break-words leading-relaxed">{detail}</li>)}</ul>}
      {!!feedback.suggestions?.length && <div className="space-y-1"><p className="font-medium">What to do next</p><p className="break-words leading-relaxed">{feedback.suggestions[0]}</p>{feedback.suggestions.length > 1 && <details><summary className="cursor-pointer">More suggestions</summary><ul className="mt-2 list-disc space-y-1 pl-4">{feedback.suggestions.slice(1).map((suggestion) => <li key={suggestion} className="break-words leading-relaxed">{suggestion}</li>)}</ul></details>}</div>}
      <p className="break-all text-xs opacity-65">Order: {feedback.id}</p>
      {onCheckStatus && <button type="button" className="btn btn-sm btn-outline mt-1" onClick={onCheckStatus}>Check order status</button>}
    </div>
    {onDismiss && <button type="button" className="btn btn-ghost btn-circle btn-xs justify-self-end" aria-label="Dismiss notification" onClick={onDismiss}>✕</button>}
  </div>
}

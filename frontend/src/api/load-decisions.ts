import { bidOnLoad, declineLoad } from './loads'
import type { ActionResult } from './types'
import { isValidBidAmount } from '../utils/bid-amount'

export class LoadDecisionError extends Error {
  readonly uncertain: boolean

  constructor(message: string, uncertain: boolean) {
    super(message)
    this.name = 'LoadDecisionError'
    this.uncertain = uncertain
  }
}

// Never retry booking actions automatically: a failed connection can hide success.
export async function submitLoadDecision(
  externalId: string,
  decision: 'bid' | 'decline',
  bidRate?: string,
): Promise<ActionResult> {
  if (decision === 'bid' && (!bidRate || !isValidBidAmount(bidRate))) {
    throw new LoadDecisionError('Enter a valid positive bid amount.', false)
  }
  let response: Response
  try {
    response = decision === 'bid'
      ? await bidOnLoad(externalId, { bid_rate: bidRate as string })
      : await declineLoad(externalId)
  } catch {
    throw new LoadDecisionError('The submission outcome is unknown. Wait for reconciliation before trying again.', true)
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const message = typeof body?.detail === 'string'
      ? body.detail
      : `The request could not be completed (HTTP ${response.status}).`
    throw new LoadDecisionError(message, response.status >= 500 || response.status === 409)
  }
  if (!body?.order || !body?.action || typeof body.sync_pending !== 'boolean') {
    throw new LoadDecisionError('The submission could not be verified. Wait for reconciliation before trying again.', true)
  }
  return body as ActionResult
}

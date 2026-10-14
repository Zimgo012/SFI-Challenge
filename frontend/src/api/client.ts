import { env } from '../config/env'

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, statusText: string, body: unknown) {
    super(`API request failed: ${status} ${statusText}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

/** Request JSON from a path relative to the configured API base URL. */
export async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T | undefined> {
  const headers = new Headers(options.headers)
  if (!headers.has('Accept')) headers.set('Accept', 'application/json')

  const response = await fetch(
    `${env.apiBaseUrl}/${endpoint.replace(/^\/+/, '')}`,
    { ...options, headers },
  )

  const text = await response.text()
  let body: unknown = text || undefined

  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      // Preserve non-JSON error responses for callers to inspect.
      if (response.ok) throw new Error('Expected a JSON response from the API')
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, body)
  }

  // The generic describes the expected response; it does not validate JSON.
  return body as T | undefined
}

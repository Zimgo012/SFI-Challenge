import { env } from '../config/env'

const apiUrl = env.apiBaseUrl

export async function apiFetch(
  path: string,
  options: RequestInit = {},
) {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  new Headers(options.headers).forEach((value, name) => {
    headers.set(name, value)
  })

  return fetch(`${apiUrl}${path}`, {
    ...options,
    headers,
  })
}

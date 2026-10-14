export function withQuery(path: string, params: object = {}): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value))
  }
  return query.size ? `${path}?${query}` : path
}

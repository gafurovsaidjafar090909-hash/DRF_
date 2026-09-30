import type { User } from './types'

export class ApiError extends Error {
  status: number
  code: string
  details: Record<string, unknown>
  constructor(status: number, code: string, details: Record<string, unknown>) {
    super(code); this.status = status; this.code = code; this.details = details
  }
}

const root = import.meta.env.VITE_API_BASE || ''
const tokenKey = 'orbit-token'
export const auth = {
  token: () => localStorage.getItem(tokenKey),
  set: (value: string) => localStorage.setItem(tokenKey, value),
  clear: () => localStorage.removeItem(tokenKey),
}

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${root}/api${path}`, {
    method, headers: { 'Content-Type': 'application/json', ...(auth.token() ? { Authorization: `Token ${auth.token()}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({})) as Record<string, unknown>
  if (!response.ok) throw new ApiError(response.status, String(data.code || data.detail || 'request_failed'), data)
  return data as T
}

export type AuthResult = { token: string; user: User }

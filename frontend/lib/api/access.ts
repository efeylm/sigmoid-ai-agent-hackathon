/**
 * Access code handling
 * The backend rejects /api requests without a valid X-Access-Code header
 * (when APP_ACCESS_CODE is set). The code is kept in localStorage.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const STORAGE_KEY = "accessCode"
export const ACCESS_INVALID_EVENT = "access-code-invalid"

export function getAccessCode(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setAccessCode(code: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    // ignore (private mode etc.)
  }
}

export function clearAccessCode(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

/** fetch() against the backend with the access code attached. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const code = getAccessCode()
  if (code) headers.set("X-Access-Code", code)

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (response.status === 401) {
    clearAccessCode()
    window.dispatchEvent(new Event(ACCESS_INVALID_EVENT))
  }
  return response
}

/** Whether the backend requires an access code at all. */
export async function isAccessCodeRequired(): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/api/auth/status`)
  if (!response.ok) throw new Error("status check failed")
  const data = await response.json()
  return Boolean(data.required)
}

/** Checks a code against the backend. */
export async function verifyAccessCode(code: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
    method: "POST",
    headers: { "X-Access-Code": code },
  })
  if (response.ok) return true
  if (response.status === 401) return false
  throw new Error(`verify failed: ${response.status}`)
}

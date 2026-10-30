import { supabase } from './supabase'

export async function apiFetch(path: string, init: RequestInit = {}) {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) throw new Error('You must sign in first.')

  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${session.access_token}`)

  const url = (import.meta.env.VITE_CLOUD_AGENT_URL || import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:5000' : 'https://remarkable-generosity-production-7d5a.up.railway.app')).replace(/\/+$/, '')
  const send = () => fetch(`${url}${path}`, {
    ...init,
    headers,
  })
  const response = await send()
  if (response.status !== 401) return response
  // Authentication rejects the request before any job or mutation is started.
  // Retry once with a refreshed session; preserve saved jobs if refresh fails.
  const { data, error } = await supabase.auth.refreshSession()
  if (error || !data.session) return response
  headers.set('Authorization', `Bearer ${data.session.access_token}`)
  return send()
}

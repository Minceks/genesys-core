import { createClient } from '@supabase/supabase-js'
import publicConfig from '../config/supabase.public.json'

// Production must use the same project as the backend and ownership database.
// Legacy Vercel variables can refer to an unrelated Supabase project.
const url = import.meta.env.DEV ? import.meta.env.VITE_SUPABASE_URL || publicConfig.url : publicConfig.url
const key = import.meta.env.DEV ? import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || publicConfig.publishableKey : publicConfig.publishableKey

// Record recovery before the SDK consumes the URL and emits its initial events.
let recoverySession = false
let accessToken = ''
export const recoveryLinkError = new URLSearchParams(window.location.hash.slice(1)).has('error')

export const supabase = url && key ? createClient(url, key, {
  global: {
    fetch: (input, init) => fetch(input, {
      ...init,
      signal: init?.signal
        ? AbortSignal.any([init.signal, AbortSignal.timeout(20000)])
        : AbortSignal.timeout(20000),
    }),
  },
}) : null
supabase?.auth.onAuthStateChange((event, session) => {
  accessToken = session?.access_token ?? ''
  if (event === 'PASSWORD_RECOVERY' && session) recoverySession = true
  if (event === 'SIGNED_OUT' || !session) recoverySession = false
})

export function hasRecoverySession() { return recoverySession }
export function clearRecoverySession() { recoverySession = false }
export function getAccessToken() { return accessToken }

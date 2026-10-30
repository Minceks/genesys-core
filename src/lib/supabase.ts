import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!url || !key) {
  throw new Error('Missing Supabase frontend configuration')
}

export const supabase = createClient(url, key)

let recoverySession = false
export const recoveryLinkError = new URLSearchParams(window.location.hash.slice(1)).has('error')
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'PASSWORD_RECOVERY' && session) recoverySession = true
  if (event === 'SIGNED_OUT' || !session) recoverySession = false
})
export function hasRecoverySession() { return recoverySession }
export function clearRecoverySession() { recoverySession = false }

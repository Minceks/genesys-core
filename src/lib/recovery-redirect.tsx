import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { supabase, hasRecoverySession } from './supabase'

// Auth can fall back to Site URL when an email redirect is not allowlisted.
// Route only SDK-validated recovery sessions; ordinary sign-in stays unchanged.
export function RecoveryRedirect() {
  const navigate = useNavigate()

  useEffect(() => {
    let mounted = true
    const recover = () => {
      if (mounted && hasRecoverySession() && window.location.pathname !== '/reset-password') {
        void navigate({ to: '/reset-password', replace: true })
      }
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' && session) recover()
    })
    // The SDK may finish parsing the email callback before this effect mounts.
    void supabase.auth.getSession().then(recover).catch(() => {})
    return () => { mounted = false; subscription.unsubscribe() }
  }, [navigate])

  return null
}

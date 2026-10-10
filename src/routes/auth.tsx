import { createRoute, Navigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Route as rootRoute } from './__root'
import { AuthPage } from '../AuthPage'
import { supabase } from '../lib/supabase'

function AuthRoute() {
  const [signedIn, setSignedIn] = useState(false)
  useEffect(() => {
    if (!supabase) return
    let active = true
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setSignedIn(Boolean(session))
    })
    supabase.auth.getSession().then(({ data }) => {
      if (active) setSignedIn(Boolean(data.session))
    }).catch(() => { /* AuthPage reports errors from sign-in attempts. */ })
    return () => { active = false; subscription.unsubscribe() }
  }, [])
  return signedIn ? <Navigate to="/account" /> : <AuthPage />
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth',
  component: AuthRoute,
})

import { useEffect, useState, type FormEvent } from 'react'
import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import { supabase, hasRecoverySession, clearRecoverySession, recoveryLinkError } from '../lib/supabase'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/reset-password',
  component: ResetPasswordPage,
})

function ResetPasswordPage() {
  const [ready, setReady] = useState(false)
  const [recovering, setRecovering] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('Checking reset link…')
  const [busy, setBusy] = useState(false)
  const [complete, setComplete] = useState(false)

  useEffect(() => {
    if (!supabase) {
      setReady(true)
      setMessage('Password reset is not configured. Please contact GeneSys support.')
      return
    }
    let mounted = true
    const refresh = (active: boolean) => {
      if (!mounted) return
      setRecovering(active)
      setReady(true)
      setMessage(active ? '' : 'Open a valid reset link from your email, or request a new one below.')
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') refresh(Boolean(session))
      if (event === 'SIGNED_OUT') refresh(false)
    })
    supabase.auth.getSession().then(({ data, error }) => {
      refresh(!error && !recoveryLinkError && Boolean(data.session) && hasRecoverySession())
    }).catch(() => refresh(false))
    return () => { mounted = false; subscription.unsubscribe() }
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!supabase || busy) return
    if (recovering && password !== confirmation) {
      setMessage('Passwords do not match.')
      return
    }
    setBusy(true)
    setMessage('')
    try {
      if (recovering) {
        const { data, error: sessionError } = await supabase.auth.getSession()
        if (sessionError || !data.session || !hasRecoverySession()) {
          setRecovering(false)
          throw new Error('Your reset session has expired. Request a new email below.')
        }
        const { error } = await supabase.auth.updateUser({ password })
        if (error) throw error
        clearRecoverySession()
        setPassword('')
        setConfirmation('')
        setComplete(true)
        setMessage('Your password has been updated.')
      } else {
        const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
          redirectTo: `${window.location.origin}/reset-password`,
        })
        if (error) throw error
        setMessage('If that address has an account, a reset email has been sent. Check your inbox.')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const inputClass = 'mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 text-slate-900 outline-none focus:ring-2 focus:ring-blue-500'
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16 text-slate-900 flex items-center justify-center">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm" aria-labelledby="reset-title">
        <a href="/" className="text-xl font-bold text-blue-600">GeneSys</a>
        <h1 id="reset-title" className="mt-8 text-2xl font-semibold">{complete ? 'Password updated' : recovering ? 'Choose a new password' : 'Reset your password'}</h1>
        {ready && !complete && supabase && (
          <form onSubmit={submit} className="mt-6 space-y-5">
            {recovering ? <>
              <label className="block text-sm font-medium">New password<input className={inputClass} type="password" minLength={8} autoComplete="new-password" required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} /></label>
              <label className="block text-sm font-medium">Confirm new password<input className={inputClass} type="password" minLength={8} autoComplete="new-password" required disabled={busy} value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
            </> : <label className="block text-sm font-medium">Email address<input className={inputClass} type="email" autoComplete="email" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} /></label>}
            <button className="w-full rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:opacity-50" disabled={busy}>{busy ? 'Please wait…' : recovering ? 'Update password' : 'Send reset email'}</button>
          </form>
        )}
        {message && <p role="status" className="mt-5 text-sm text-slate-600">{message}</p>}
        <a href="/build" className="mt-6 inline-block text-sm font-medium text-blue-600">Return to GeneSys</a>
      </section>
    </main>
  )
}

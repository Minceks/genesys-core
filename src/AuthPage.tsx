import { useState } from 'react'
import { supabase } from './lib/supabase'

type Mode = 'signin' | 'signup' | 'forgot'

export function AuthPage() {
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setMessage('')
    setBusy(true)

    try {
      if (!supabase) throw new Error('Authentication is not configured.')
      if (mode === 'forgot') {
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        })
        if (error) throw error
        setMessage('If that address has an account, a reset email has been sent.')
      } else if (mode === 'signup') {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth` },
        })
        if (error) throw error

        setMessage(
          data.session
            ? 'Account created.'
            : 'Check your email to confirm your account.',
        )
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
        setMessage('Signed in. Opening your workspace…')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  async function signInWithGoogle() {
    if (!supabase) { setMessage('Authentication is not configured.'); return }
    setMessage('')
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth` },
    })
    if (error) setMessage(error.message)
  }

  return (
    <main>
      <h1>
        {mode === 'signup' ? 'Create account' :
         mode === 'forgot' ? 'Reset password' : 'Sign in'}
      </h1>

      <form onSubmit={submit}>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        {mode !== 'forgot' && (
          <label>
            Password
            <input
              type="password"
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        )}

        <button disabled={busy}>
          {busy ? 'Please wait…' :
           mode === 'signup' ? 'Create account' :
           mode === 'forgot' ? 'Send reset email' : 'Sign in'}
        </button>
      </form>

      {mode !== 'forgot' && (
        <button type="button" onClick={signInWithGoogle}>
          Continue with Google
        </button>
      )}

      {mode === 'signin' && (
        <>
          <button type="button" onClick={() => setMode('signup')}>Create account</button>
          <button type="button" onClick={() => setMode('forgot')}>Forgot password?</button>
        </>
      )}
      {mode !== 'signin' && (
        <button type="button" onClick={() => setMode('signin')}>Back to sign in</button>
      )}

      {message && <p role="status">{message}</p>}
    </main>
  )
}

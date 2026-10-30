import { useState } from 'react'
import { ArrowLeft, ArrowUpRight, Check } from 'lucide-react'
import { BrandMark } from '@/components/genesys/brand'
import { supabase } from './lib/supabase'

type Mode = 'signin' | 'signup' | 'forgot'

export function AuthPage() {
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('error_description') || '')
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setMessage('')
    setBusy(true)

    try {
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
    setMessage('')
    setBusy(true)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/auth` },
      })
      if (error) throw error
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Google sign-in could not start. Try signing in with email.')
    } finally {
      setBusy(false)
    }
  }

  function changeMode(next: Mode) {
    setMode(next)
    setMessage('')
    setPassword('')
  }

  const title = mode === 'signup' ? 'Create account' : mode === 'forgot' ? 'Reset password' : 'Sign in'
  const inputStyle = 'g-input'

  return (
    <main className="g-page g-glow px-6 py-7 sm:px-10">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
        <a href="/" className="g-brand"><BrandMark />GeneSys</a>
        <a href="/" className="inline-flex min-h-11 items-center gap-2 text-sm text-[var(--muted)] hover:text-white"><ArrowLeft size={16} /> Back to home</a>
      </header>
      <div className="mx-auto grid max-w-6xl items-center gap-12 py-12 sm:py-20 lg:grid-cols-2 lg:gap-24">
        <section className="hidden lg:block" aria-label="About your workspace">
          <p className="text-sm font-medium text-[var(--accent-text)]">Your next idea starts here</p>
          <h2 className="mt-6 text-6xl font-semibold font-extrabold leading-[1.05]">Build what<br />you can<br /><span className="g-gradient-text">imagine.</span></h2>
          <p className="mt-7 max-w-md text-lg leading-relaxed text-[var(--muted)]">Build websites and applications with AI, review the results, and keep shaping your ideas.</p>
          <ul className="mt-9 space-y-4 text-sm text-slate-300">{['Plan, discuss, and build in one place', 'Desktop and phone previews', 'Saved projects and build progress'].map(item => <li key={item} className="flex items-center gap-3"><Check size={17} className="text-blue-400" />{item}</li>)}</ul>
        </section>
        <section className="mx-auto w-full max-w-md g-card p-6 shadow-2xl sm:p-9" aria-labelledby="auth-title">
          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-[var(--accent-text)]">Your GeneSys workspace</p>
          <h1 id="auth-title" className="text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-3 text-sm leading-relaxed text-[var(--muted)]">{mode === 'signup' ? 'Create an account to save your projects and start building.' : mode === 'forgot' ? 'Enter your email and we will send you a password reset link.' : 'Welcome back. Continue building your next idea.'}</p>
          <form onSubmit={submit} className="mt-7 space-y-5" aria-busy={busy}>
            <div><label htmlFor="auth-email" className="text-sm font-medium text-slate-200">Email</label><input id="auth-email" className={inputStyle} type="email" autoComplete="email" placeholder="you@example.com" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} /></div>
            {mode !== 'forgot' && <div><div className="flex flex-wrap items-center justify-between gap-2"><label htmlFor="auth-password" className="text-sm font-medium text-slate-200">Password</label>{mode === 'signin' && <button type="button" disabled={busy} onClick={() => changeMode('forgot')} className="min-h-8 text-xs text-[var(--accent-text)] hover:text-blue-200 disabled:opacity-50">Forgot password?</button>}</div><input id="auth-password" className={inputStyle} type="password" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} minLength={mode === 'signup' ? 8 : undefined} required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} />{mode === 'signup' && <p className="mt-2 text-xs text-slate-500">Use at least 8 characters.</p>}</div>}
            {message && <p role="status" aria-live="polite" className="break-words rounded-xl border border-blue-400/20 bg-[var(--accent)]/5 p-4 text-sm leading-relaxed text-blue-200">{message}</p>}
            <button type="submit" disabled={busy} className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--accent-hover)] disabled:cursor-wait disabled:opacity-60">{busy ? 'Please wait…' : mode === 'forgot' ? 'Send reset email' : title}{!busy && <ArrowUpRight size={17} />}</button>
          </form>
          {mode !== 'forgot' && <><div className="my-6 flex items-center gap-4 text-xs text-slate-500"><span className="h-px flex-1 bg-white/10" />or<span className="h-px flex-1 bg-white/10" /></div><button type="button" disabled={busy} onClick={signInWithGoogle} className="min-h-12 w-full rounded-xl border border-white/15 bg-white/[0.02] px-4 py-3 text-sm font-medium hover:bg-white/5 disabled:opacity-50">Continue with Google</button></>}
          <div className="mt-7 border-t border-white/10 pt-6 text-center text-sm text-[var(--muted)]">{mode === 'signin' ? <>New to GeneSys? <button type="button" disabled={busy} onClick={() => changeMode('signup')} className="min-h-11 font-medium text-[var(--accent-text)] hover:text-blue-200">Create account</button></> : <button type="button" disabled={busy} onClick={() => changeMode('signin')} className="min-h-11 font-medium text-[var(--accent-text)] hover:text-blue-200">Back to sign in</button>}</div>
        </section>
      </div>
    </main>
  )
}

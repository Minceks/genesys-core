import { useState } from 'react'
import { ArrowLeft, ArrowRight, Cpu, Layers, Loader2, ShieldCheck, Sparkles } from 'lucide-react'
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
    if (busy) return
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
          email: email.trim(),
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth` },
        })
        if (error) throw error

        setMessage(
          data.session
            ? 'Account created.'
            : 'Check your email to confirm your account.',
        )
        if (data.session) window.location.assign('/account')
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        })
        if (error) throw error
        if (!data.session) throw new Error('Sign-in did not establish a session. Please try again.')
        setMessage('Signed in. Opening your workspace…')
        window.location.assign('/account')
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  function changeMode(next: Mode) { setMode(next); setMessage(''); setPassword('') }

  async function signInWithGoogle() {
    if (busy) return
    if (!supabase) { setMessage('Authentication is not configured.'); return }
    setBusy(true)
    setMessage('')
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/auth` },
      })
      if (error) throw error
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Google sign-in failed.')
    } finally { setBusy(false) }
  }

  const title = mode === 'signup' ? 'Create account' : mode === 'forgot' ? 'Reset password' : 'Sign in'
  const subtitle = mode === 'signup' ? 'Your next idea starts here.' : mode === 'forgot' ? 'We?ll email you a link to choose a new password.' : 'Welcome back. Pick up where you left off.'
  const inputClass = 'mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 disabled:bg-slate-50'

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8">
          <a href="/" className="flex items-center gap-2.5 no-underline" aria-label="GeneSys home">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20"><Cpu size={21} /></span>
            <span className="text-[17px] font-extrabold tracking-tight">GeneSys<span className="text-blue-600">.</span></span>
          </a>
          <a href="/" className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-blue-600"><ArrowLeft size={15} /> Back to home</a>
        </div>
      </header>
      <div className="mx-auto grid min-h-[calc(100vh-72px)] max-w-6xl items-center gap-12 px-5 py-12 sm:px-8 lg:grid-cols-2 lg:gap-20 lg:py-20">
        <section className="hidden lg:block">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700"><Sparkles size={14} /> From idea to working app</span>
          <h2 className="mt-6 text-5xl font-extrabold leading-[1.12] tracking-tight">A workspace for<br />your <span className="text-blue-600">next big idea.</span></h2>
          <p className="mt-6 max-w-md text-lg leading-8 text-slate-500">Build with your AI agent, explore your projects, and bring your ideas to life in one place.</p>
          <div className="mt-10 space-y-5">
            <div className="flex gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-blue-600"><Layers size={20} /></span><div><p className="font-semibold">Your projects, together</p><p className="mt-1 text-sm text-slate-500">Return to your workspace whenever inspiration strikes.</p></div></div>
            <div className="flex gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-blue-600"><ShieldCheck size={20} /></span><div><p className="font-semibold">An account of your own</p><p className="mt-1 text-sm text-slate-500">Manage your projects and account from your dashboard.</p></div></div>
          </div>
        </section>
        <section className="mx-auto w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-xl shadow-slate-200/40 sm:p-10" aria-labelledby="auth-title">
          <h1 id="auth-title" className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="mt-3 text-sm leading-6 text-slate-500">{subtitle}</p>
          {mode !== 'forgot' && <>
            <button type="button" disabled={busy} onClick={signInWithGoogle} className="mt-7 flex w-full items-center justify-center gap-3 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold transition hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-50"><span aria-hidden="true" className="text-base font-bold text-blue-600">G</span> Continue with Google</button>
            <div className="my-6 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-100" /> or continue with email <span className="h-px flex-1 bg-slate-100" /></div>
          </>}
          <form onSubmit={submit} className={mode === 'forgot' ? 'mt-7 space-y-5' : 'space-y-5'}>
            <label className="block text-sm font-semibold">Email<input className={inputClass} type="email" autoComplete="email" placeholder="you@example.com" required disabled={busy} value={email} onChange={e => setEmail(e.target.value)} /></label>
            {mode !== 'forgot' && <label className="block text-sm font-semibold"><span className="flex items-center justify-between">Password{mode === 'signin' && <button type="button" disabled={busy} onClick={() => changeMode('forgot')} className="text-xs font-medium text-blue-600 hover:text-blue-700">Forgot password?</button>}</span><input className={inputClass} type="password" autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} minLength={mode === 'signup' ? 8 : undefined} placeholder={mode === 'signup' ? 'At least 8 characters' : 'Enter your password'} required disabled={busy} value={password} onChange={e => setPassword(e.target.value)} /></label>}
            <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3.5 text-sm font-semibold text-white shadow-md shadow-blue-600/20 transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50">{busy ? <><Loader2 size={16} className="animate-spin" /> Please wait?</> : <>{mode === 'signup' ? 'Create account' : mode === 'forgot' ? 'Send reset email' : 'Sign in'}<ArrowRight size={16} /></>}</button>
          </form>
          {message && <p role="status" className="mt-5 rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm leading-6 text-blue-900">{message}</p>}
          <div className="mt-7 border-t border-slate-100 pt-6 text-center text-sm text-slate-500">{mode === 'signin' ? <>New to GeneSys? <button type="button" disabled={busy} onClick={() => changeMode('signup')} className="font-semibold text-blue-600 hover:text-blue-700">Create account</button></> : <button type="button" disabled={busy} onClick={() => changeMode('signin')} className="font-semibold text-blue-600 hover:text-blue-700">Back to sign in</button>}</div>
          {mode === 'signup' && <p className="mt-5 text-center text-xs leading-5 text-slate-400">By creating an account, you agree to our <a href="/terms" className="underline hover:text-blue-600">Terms &amp; Conditions</a>.</p>}
        </section>
      </div>
    </main>
  )
}

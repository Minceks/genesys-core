import { useEffect, useState } from 'react'
import { createRoute, Navigate } from '@tanstack/react-router'
import type { Session } from '@supabase/supabase-js'
import { ArrowRight, LogOut, Plus, Sparkles } from 'lucide-react'
import { Route as rootRoute } from './__root'
import { Brand } from '@/components/genesys/brand'
import { supabase } from '../lib/supabase'

export const Route = createRoute({ getParentRoute: () => rootRoute, path: '/account', component: AccountDashboard })
type Project = { id: string; name: string; created_at: string }
const THUMBNAILS = ['linear-gradient(135deg,#6470ff,#38bdf8)', 'linear-gradient(135deg,#8b5cf6,#ec4899)', 'linear-gradient(135deg,#10b981,#0ea5e9)', 'linear-gradient(135deg,#f97316,#db2777)']
const thumbnail = (id: string) => THUMBNAILS[[...id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % THUMBNAILS.length]

function AccountDashboard() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const userId = session?.user.id
  const [waitingIdea] = useState(() => { try { return sessionStorage.getItem('genesys_starter_prompt') || '' } catch { return '' } })
  useEffect(() => {
    let active = true
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, next) => {
      if (active) { setSession(next); setReady(true) }
    })
    supabase.auth.getSession().then(({ data, error }) => {
      if (active) { setSession(data.session); setReady(true); if (error) setMessage(error.message) }
    }).catch(() => { if (active) { setReady(true); setMessage('Unable to load your session.') } })
    return () => { active = false; subscription.unsubscribe() }
  }, [])
  useEffect(() => {
    let active = true
    setProjects([])
    if (!userId) return
    setBusy(true)
    supabase.from('projects').select('id,name,created_at').order('created_at', { ascending: false })
      .then(({ data, error }) => {
        if (!active) return
        if (error) setMessage(error.message)
        else setProjects(data ?? [])
        setBusy(false)
      })
    return () => { active = false }
  }, [userId])

  async function action(kind: 'create' | 'reset' | 'signout') {
    if (busy) return
    setBusy(true); setMessage('')
    try {
      if (kind === 'create') {
        const { data, error } = await supabase.from('projects').insert({ name: 'Untitled project' }).select('id,name,created_at').single()
        if (error) throw error
        setProjects(previous => [data, ...previous])
        setMessage('Project created. Select it below to open the builder.')
        try {
          if (sessionStorage.getItem('genesys_starter_prompt')) {
            sessionStorage.setItem('genesys_idea_project', data.id)
            window.location.assign(`/build?projectId=${encodeURIComponent(data.id)}`)
          }
        } catch { /* The project is created even if browser storage is unavailable. */ }
      } else if (kind === 'reset') {
        if (!session?.user.email) throw new Error('No email address is available for this account.')
        const { error } = await supabase.auth.resetPasswordForEmail(session.user.email, { redirectTo: `${window.location.origin}/reset-password` })
        if (error) throw error
        setMessage('Password reset email requested. Check your inbox.')
      } else {
        const { error } = await supabase.auth.signOut()
        if (error) throw error
      }
    } catch (error) {
      setMessage(error && typeof error === 'object' && 'message' in error ? String(error.message) : 'Unable to complete this action.')
    } finally { setBusy(false) }
  }

  if (!ready) return <main className="g-page grid place-items-center" role="status"><span className="text-[var(--muted)]">Loading your projects…</span></main>
  if (!session) return <Navigate to="/auth" />
  return <main className="g-page g-glow">
    <header className="g-nav"><nav aria-label="Workspace" className="g-container"><div className="g-nav-inner"><Brand /><div className="g-nav-actions"><a href="/" className="g-btn g-btn-ghost g-btn-sm">Home</a><button type="button" disabled={busy} onClick={() => action('signout')} className="g-btn g-btn-ghost g-btn-sm"><LogOut size={15} />Sign out</button></div></div></nav></header>
    <div className="g-container py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="m-0 text-3xl font-extrabold sm:text-4xl">Your projects</h1><p className="mt-2 text-[var(--muted)]">Pick up where you left off, or start something new.</p></div>
        <button type="button" disabled={busy} onClick={() => action('create')} className="g-btn g-btn-primary"><Plus size={17} />{busy ? 'Please wait…' : 'New project'}</button>
      </div>
      {waitingIdea && <div className="wk-idea mt-6"><p><strong className="inline-flex items-center gap-2"><Sparkles size={15} />Your idea is ready to build</strong><small>{waitingIdea}</small></p><button type="button" disabled={busy} onClick={() => action('create')} className="g-btn g-btn-primary g-btn-sm">Start this project <ArrowRight size={15} /></button></div>}
      {message && <p role="status" className="g-notice mt-6">{message}</p>}
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_300px]">
        <section id="projects" aria-label="Projects">
          <div className="wk-grid">
            {busy && projects.length === 0 && [0, 1, 2].map(item => <div key={item} className="g-card g-skeleton" style={{ height: 212 }} />)}
            {projects.map(project => <a key={project.id} href={`/build?projectId=${encodeURIComponent(project.id)}`} className="g-card wk-card"><div className="wk-thumb" style={{ background: thumbnail(project.id) }} aria-hidden="true">{project.name.trim().charAt(0).toUpperCase() || 'G'}</div><div className="wk-body"><h3>{project.name}</h3><p>Created {new Date(project.created_at).toLocaleDateString()}</p></div></a>)}
            {!busy && <button type="button" onClick={() => action('create')} className="wk-new"><Plus size={22} />{projects.length ? 'New project' : 'Create your first project'}</button>}
          </div>
        </section>
        <aside id="profile" className="g-card h-fit p-5">
          <h2 className="m-0 text-base font-bold">Account</h2>
          <p className="mt-4 mb-0 text-xs text-[var(--faint)]">Email</p><p className="m-0 break-all text-sm">{session.user.email ?? 'No email address'}</p>
          <p className="mt-4 mb-0 text-xs text-[var(--faint)]">Member since</p><p className="m-0 text-sm">{new Date(session.user.created_at).toLocaleDateString()}</p>
          <button type="button" disabled={busy || !session.user.email} onClick={() => action('reset')} className="g-btn g-btn-secondary g-btn-sm mt-5 w-full">Send password reset email</button>
        </aside>
      </div>
    </div>
  </main>
}

import { useEffect, useState } from 'react'
import { createRoute, Navigate } from '@tanstack/react-router'
import type { Session } from '@supabase/supabase-js'
import { Route as rootRoute } from './__root'
import { supabase } from '../lib/supabase'

export const Route = createRoute({ getParentRoute: () => rootRoute, path: '/account', component: AccountDashboard })
type Project = { id: string; name: string; created_at: string }

function AccountDashboard() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const userId = session?.user.id
  useEffect(() => {
    if (!supabase) { setReady(true); setMessage('Authentication is not configured.'); return }
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
    if (!userId || !supabase) return
    setBusy(true)
    supabase.from('projects').select('id,name,created_at').order('created_at', { ascending: false })
      .then(({ data, error }) => {
        if (!active) return
        if (error) setMessage(error.message)
        else setProjects(data ?? [])
        setBusy(false)
      }).catch(() => { if (active) { setMessage('Unable to load projects. Please refresh and retry.'); setBusy(false) } })
    return () => { active = false }
  }, [userId])

  async function action(kind: 'create' | 'reset' | 'signout') {
    if (busy) return
    setBusy(true); setMessage('')
    try {
      if (!supabase) throw new Error('Authentication is not configured.')
      if (kind === 'create') {
        const { data, error } = await supabase.from('projects').insert({ name: 'Untitled project' }).select('id,name,created_at').single()
        if (error) throw error
        setProjects(previous => [data, ...previous])
        setMessage('Project created. Select it below to open the builder.')
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

  if (!ready) return <main className="min-h-screen bg-slate-50 p-12 text-slate-900" role="status">Loading your dashboard…</main>
  if (!session) return <Navigate to="/auth" />
  return <main className="min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b bg-white px-6 py-5"><nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4"><a className="text-xl font-bold text-blue-600" href="/">GeneSys</a><div className="flex gap-5 text-sm"><a href="/">Home</a><a href="#projects">My projects</a><a href="#profile">Profile</a><button disabled={busy} onClick={() => action('signout')}>Sign out</button></div></nav></header>
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-3xl font-semibold">Your workspace</h1><p className="mt-2 text-slate-500">Manage your projects and account.</p>
      {message && <p role="status" className="mt-6 rounded-xl border border-blue-100 bg-blue-50 p-4 text-blue-900">{message}</p>}
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_320px]">
        <section id="projects"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">My projects</h2><button disabled={busy} onClick={() => action('create')} className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Please wait…' : 'New project'}</button></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">{projects.map(project => <a key={project.id} href={`/build?projectId=${encodeURIComponent(project.id)}`} className="rounded-2xl border border-slate-200 bg-white p-6 hover:border-blue-400"><h3 className="font-semibold">{project.name}</h3><p className="mt-2 text-xs text-slate-500">Created {new Date(project.created_at).toLocaleDateString()}</p><span className="mt-6 inline-block text-sm font-semibold text-blue-600">Open project →</span></a>)}</div>
          {!busy && projects.length === 0 && <p className="mt-5 rounded-2xl border border-dashed p-8 text-slate-500">Create your first project to get started.</p>}
        </section>
        <aside id="profile" className="h-fit rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-xl font-semibold">Your profile</h2><p className="mt-5 text-xs font-semibold uppercase text-slate-400">Email</p><p className="mt-1 break-all text-sm">{session.user.email ?? 'No email address'}</p><p className="mt-5 text-xs font-semibold uppercase text-slate-400">Member since</p><p className="mt-1 text-sm">{new Date(session.user.created_at).toLocaleDateString()}</p><button disabled={busy || !session.user.email} onClick={() => action('reset')} className="mt-6 block text-sm font-semibold text-blue-600 disabled:opacity-50">Send password reset email</button><button disabled={busy} onClick={() => action('signout')} className="mt-4 text-sm text-slate-600">Sign out</button></aside>
      </div>
    </div>
  </main>
}

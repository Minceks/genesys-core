import { useEffect, useRef, useState } from 'react'
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
  const [projectName, setProjectName] = useState('')
  const [projectError, setProjectError] = useState('')
  const projectDialog = useRef<HTMLDialogElement>(null)
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
    if (kind === 'create' && (!projectName.trim() || projectName.trim().length > 200)) { setProjectError('Enter a project name of 1?200 characters.'); return }
    setProjectError('')
    setBusy(true); setMessage('')
    try {
      if (!supabase) throw new Error('Authentication is not configured.')
      if (kind === 'create') {
        const { data, error } = await supabase.from('projects').insert({ name: projectName.trim() }).select('id,name,created_at').single()
        if (error) throw error
        setProjects(previous => [data, ...previous])
        projectDialog.current?.close()
        setProjectName('')
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
      const text = error && typeof error === 'object' && 'message' in error ? String(error.message) : 'Unable to complete this action.'
      if (kind === 'create') setProjectError(text)
      else setMessage(text)
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
        <section id="projects"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">My projects</h2><button disabled={busy} onClick={() => { setProjectName(''); setProjectError(''); projectDialog.current?.showModal() }} className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Please wait…' : 'New project'}</button></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">{projects.map(project => <a key={project.id} href={`/build?projectId=${encodeURIComponent(project.id)}`} className="rounded-2xl border border-slate-200 bg-white p-6 hover:border-blue-400"><h3 className="font-semibold">{project.name}</h3><p className="mt-2 text-xs text-slate-500">Created {new Date(project.created_at).toLocaleDateString()}</p><span className="mt-6 inline-block text-sm font-semibold text-blue-600">Open project →</span></a>)}</div>
          {!busy && projects.length === 0 && <p className="mt-5 rounded-2xl border border-dashed p-8 text-slate-500">Create your first project to get started.</p>}
        </section>
        <aside id="profile" className="h-fit rounded-2xl border border-slate-200 bg-white p-6"><h2 className="text-xl font-semibold">Your profile</h2><p className="mt-5 text-xs font-semibold uppercase text-slate-400">Email</p><p className="mt-1 break-all text-sm">{session.user.email ?? 'No email address'}</p><p className="mt-5 text-xs font-semibold uppercase text-slate-400">Member since</p><p className="mt-1 text-sm">{new Date(session.user.created_at).toLocaleDateString()}</p><button disabled={busy || !session.user.email} onClick={() => action('reset')} className="mt-6 block text-sm font-semibold text-blue-600 disabled:opacity-50">Send password reset email</button><button disabled={busy} onClick={() => action('signout')} className="mt-4 text-sm text-slate-600">Sign out</button></aside>
      </div>
    </div>
    <dialog ref={projectDialog} aria-labelledby="new-project-title" onCancel={event => { if (busy) event.preventDefault() }} className="m-auto w-[calc(100%-2rem)] max-w-md rounded-3xl border border-slate-200 bg-white p-7 text-slate-900 shadow-xl backdrop:bg-slate-900/40">
      <h2 id="new-project-title" className="text-xl font-semibold">New project</h2>
      <p className="mt-2 text-sm text-slate-500">Give your project a name. You can open it in the builder after creating it.</p>
      <form className="mt-6" onSubmit={event => { event.preventDefault(); void action('create') }}>
        <label className="block text-sm font-semibold">Project name<input autoFocus required maxLength={200} disabled={busy} value={projectName} onChange={event => setProjectName(event.target.value)} placeholder="e.g. My portfolio" className="mt-2 block w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10" /></label>
        {projectError && <p role="alert" className="mt-3 text-sm text-red-700">{projectError}</p>}
        <div className="mt-6 flex justify-end gap-3"><button type="button" disabled={busy} onClick={() => projectDialog.current?.close()} className="rounded-xl px-4 py-3 text-sm font-semibold text-slate-600">Cancel</button><button disabled={busy || !projectName.trim()} className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Creating?' : 'Create project'}</button></div>
      </form>
    </dialog>
  </main>
}

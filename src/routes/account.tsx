import { MoreHorizontal, Trash2 } from "lucide-react";
import "@/components/genesys/polish.css";
import { useEffect, useRef, useState } from 'react'
import { createRoute, Navigate } from '@tanstack/react-router'
import type { Session } from '@supabase/supabase-js'
import { Route as rootRoute } from './__root'
import { supabase } from '../lib/supabase'
import { ProfileSettings } from '../components/ProfileSettings'
import { CLOUD_AGENT_URL } from '../utils/ai.functions'

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
  const [usage, setUsage] = useState<{ hourlyRemaining: number; hourlyLimit: number; dailyRemaining: number | null; dailyLimit: number; dailyUnlimited?: boolean; dailyTokenLimit?: number | null; dailyTokensUsed?: number; dailyTokensRemaining?: number | null; tokenResetAt?: number } | null>(null)
  const projectDialog = useRef<HTMLDialogElement>(null)
  const [projectMenu, setProjectMenu] = useState<{ project: Project; x: number; y: number } | null>(null)
  const [deletingProject, setDeletingProject] = useState<Project | null>(null)
  const [unpublishOnDelete, setUnpublishOnDelete] = useState(true)
  const deleteDialog = useRef<HTMLDialogElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!projectMenu) return
    menuRef.current?.querySelector('button')?.focus()
    const close = () => setProjectMenu(null)
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') close() }
    window.addEventListener('click', close)
    window.addEventListener('keydown', escape)
    window.addEventListener('resize', close)
    window.addEventListener('scroll', close, true)
    return () => { window.removeEventListener('click', close); window.removeEventListener('keydown', escape); window.removeEventListener('resize', close); window.removeEventListener('scroll', close, true) }
  }, [projectMenu])
  function openProjectMenu(project: Project, x: number, y: number) {
    if (busy) return
    setProjectMenu({ project, x: Math.max(8, Math.min(x, window.innerWidth - 200)), y: Math.max(8, Math.min(y, window.innerHeight - 65)) })
  }
  async function deleteProject() {
    if (!deletingProject || busy || !supabase || !userId) return
    setBusy(true); setMessage('')
    try {
      const response = await fetch(`${CLOUD_AGENT_URL}/api/projects/${deletingProject.id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${session?.access_token}`, 'Content-Type':'application/json' },
        body: JSON.stringify({ unpublish: unpublishOnDelete }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Project cleanup failed. Please retry.')
      setProjects(previous => previous.filter(project => project.id !== deletingProject.id))
      setMessage('Project deleted from your workspace.')
      deleteDialog.current?.close()
      setDeletingProject(null)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to delete the project. Please try again.') }
    finally { setBusy(false) }
  }
  const userId = session?.user.id
  useEffect(() => {
    let active = true
    setUsage(null)
    if (session?.access_token) fetch(`${CLOUD_AGENT_URL}/usage`, { headers: { Authorization: `Bearer ${session.access_token}` }, signal: AbortSignal.timeout(15000) })
      .then(response => response.ok ? response.json() : null).then(data => { if (active) setUsage(data) }).catch(() => {})
    return () => { active = false }
  }, [session?.access_token])
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
  return <main className="genesys-workspace min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b bg-white px-6 py-5"><nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4"><a className="text-xl font-bold text-blue-600" href="/">GeneSys</a><div className="flex flex-wrap gap-x-5 gap-y-3 text-sm"><a href="/">Home</a><a href="#projects">My projects</a><a href="#profile">Profile</a><button disabled={busy} onClick={() => action('signout')}>Sign out</button></div></nav></header>
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-blue-600">Your creative workspace</div><h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">A little idea. Your next project.</h1><p className="mt-3 max-w-xl text-sm leading-6 text-slate-500">Everything you are building, in one place. Open a project to pick up where you left off.</p>
      <div className="mt-7 flex flex-wrap gap-3"><span className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500"><strong className="mr-2 text-slate-900">{projects.length}</strong> {projects.length === 1 ? 'project' : 'projects'} in your workspace</span><span className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">Private workspace / Beta</span></div>
      {usage && <p className="mt-4 text-sm text-slate-600">Beta builds available: <strong>{usage.hourlyRemaining}/{usage.hourlyLimit}</strong> this hour · <strong>{usage.dailyUnlimited ? "Unlimited" : `${usage.dailyRemaining}/${usage.dailyLimit}`}</strong> today.</p>}
      {usage && <p className="mt-2 text-sm text-slate-500">Daily model usage: {(usage.dailyTokensUsed ?? 0).toLocaleString()} tokens / {usage.dailyUnlimited ? 'Unlimited for your account' : (usage.dailyTokenLimit ?? 0).toLocaleString()}. {usage.tokenResetAt ? `Resets ${new Date(usage.tokenResetAt).toLocaleString()}.` : ''}</p>}
      {message && <p role="status" className="mt-6 rounded-xl border border-blue-100 bg-blue-50 p-4 text-blue-900">{message}</p>}
      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_320px]">
        <section id="projects"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">My projects</h2><button disabled={busy} onClick={() => { setProjectName(''); setProjectError(''); projectDialog.current?.showModal() }} className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Please wait…' : 'New project'}</button></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">{projects.map(project => <article key={project.id} onContextMenu={event => { event.preventDefault(); openProjectMenu(project, event.clientX, event.clientY) }} className="relative rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-blue-300 hover:shadow-md">
            <a href={`/build?projectId=${encodeURIComponent(project.id)}`} className="block p-6 pr-12"><div aria-hidden="true" className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-lg font-semibold text-blue-600">{project.name.charAt(0).toUpperCase()}</div><h3 className="truncate text-base font-semibold tracking-tight">{project.name}</h3><p className="mt-2 text-xs text-slate-500">Created {new Date(project.created_at).toLocaleDateString()}</p><span className="mt-6 inline-block text-sm font-semibold text-blue-600">Open project &rarr;</span></a>
            <button type="button" aria-label={`Actions for ${project.name}`} aria-haspopup="menu" aria-expanded={projectMenu?.project.id === project.id} disabled={busy} onClick={event => { event.stopPropagation(); const rect = event.currentTarget.getBoundingClientRect(); openProjectMenu(project, rect.right - 190, rect.bottom + 4) }} className="absolute right-3 top-3 rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"><MoreHorizontal size={20} /></button>
          </article>)}</div>
          {!busy && projects.length === 0 && <p className="mt-5 rounded-2xl border border-dashed p-8 text-slate-500">Your workspace is a blank canvas. Choose New project, give it a name, and tell GeneSys what you want to create.</p>}
        </section>
        <ProfileSettings user={session.user} busy={busy} onReset={() => void action('reset')} onSignOut={() => void action('signout')} />
      </div>
    </div>
    {projectMenu && <div ref={menuRef} role="menu" aria-label="Project actions" style={{ left: projectMenu.x, top: projectMenu.y }} className="fixed z-50 w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">
      <button type="button" role="menuitem" onClick={() => { setDeletingProject(projectMenu.project); setProjectMenu(null); deleteDialog.current?.showModal() }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"><Trash2 size={16} /> Delete project</button>
    </div>}
    <dialog ref={deleteDialog} aria-labelledby="delete-project-title" onCancel={event => { if (busy) event.preventDefault() }} className="m-auto w-[calc(100%-2rem)] max-w-md rounded-3xl border border-slate-200 bg-white p-7 text-slate-900 shadow-xl backdrop:bg-slate-900/40">
      <h2 id="delete-project-title" className="text-xl font-semibold">Delete project?</h2>
      <p className="mt-3 break-words text-sm leading-6 text-slate-600">Remove <strong>{deletingProject?.name}</strong> from your workspace? This cannot be undone. Its workspace will be archived.</p>
      <label className="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={unpublishOnDelete} onChange={event => setUnpublishOnDelete(event.target.checked)} /> Also unpublish its public links</label>
      <div className="mt-6 flex justify-end gap-3"><button type="button" disabled={busy} onClick={() => deleteDialog.current?.close()} className="rounded-xl px-4 py-3 text-sm font-semibold text-slate-600">Cancel</button><button type="button" disabled={busy} onClick={() => void deleteProject()} className="rounded-xl bg-red-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Deleting...' : 'Delete project'}</button></div>
    </dialog>
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

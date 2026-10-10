import { useEffect, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

export function ProfileSettings({ user, busy, onReset, onSignOut }: { user: User; busy: boolean; onReset: () => void; onSignOut: () => void }) {
  const [firstName, setFirstName] = useState('')
  const [surname, setSurname] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => {
    setFirstName(user.user_metadata.first_name || '')
    setSurname(user.user_metadata.last_name || '')
  }, [user.id, user.user_metadata.first_name, user.user_metadata.last_name])
  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (saving || busy) return
    setSaving(true); setMessage('')
    try {
      if (!firstName.trim() || !surname.trim()) throw new Error('Enter your first name and surname.')
      if (!supabase) throw new Error('Authentication is unavailable.')
      const { error } = await supabase.auth.updateUser({ data: {
        first_name: firstName.trim(), last_name: surname.trim(), full_name: `${firstName.trim()} ${surname.trim()}`,
      } })
      if (error) throw error
      setMessage('Profile updated.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Your profile could not be saved.') }
    finally { setSaving(false) }
  }
  const disabled = saving || busy
  return <aside id="profile" className="h-fit rounded-2xl border border-slate-200 bg-white p-6">
    <h2 className="text-xl font-semibold">Your profile</h2>
    {(user.user_metadata.full_name || user.user_metadata.name) && <p className="mt-2 font-medium text-slate-600">{user.user_metadata.full_name || user.user_metadata.name}</p>}
    <form onSubmit={save} className="mt-5 space-y-4">
      <label className="block text-sm font-medium">First name<input autoComplete="given-name" required maxLength={100} disabled={disabled} value={firstName} onChange={event => setFirstName(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-blue-500 focus:outline-none" /></label>
      <label className="block text-sm font-medium">Surname<input autoComplete="family-name" required maxLength={100} disabled={disabled} value={surname} onChange={event => setSurname(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 focus:border-blue-500 focus:outline-none" /></label>
      <button disabled={disabled} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Save profile'}</button>
    </form>
    {message && <p role="status" className="mt-3 text-sm text-blue-800">{message}</p>}
    <p className="mt-5 text-xs font-semibold uppercase text-slate-400">Email</p><p className="mt-1 break-all text-sm">{user.email ?? 'No email address'}</p>
    <p className="mt-5 text-xs font-semibold uppercase text-slate-400">Member since</p><p className="mt-1 text-sm">{new Date(user.created_at).toLocaleDateString()}</p>
    <button disabled={disabled || !user.email} onClick={onReset} className="mt-6 block text-sm font-semibold text-blue-600 disabled:opacity-50">Send password reset email</button>
    <button disabled={disabled} onClick={onSignOut} className="mt-4 text-sm text-slate-600">Sign out</button>
  </aside>
}

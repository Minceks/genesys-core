import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

export type BuilderMode = 'build' | 'plan' | 'discuss';

export function BuilderControls({ projectId, mode, onModeChange, busy }: {
  projectId: string; mode: BuilderMode; onModeChange: (mode: BuilderMode) => void; busy: boolean;
}) {
  const [instructions, setInstructions] = useState('');
  const [paths, setPaths] = useState('');
  const [revision, setRevision] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoaded(false);
    void apiFetch(`/builder/controls?projectId=${encodeURIComponent(projectId)}`)
      .then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Unable to load AI controls.');
        if (active) { setInstructions(data.instructions); setPaths(data.lockedPaths.join('\n')); setRevision(data.revision); setLoaded(true); setNotice(''); }
      }).catch(error => { if (active) setNotice(error.message); });
    return () => { active = false; };
  }, [projectId, reload]);

  async function save() {
    setSaving(true); setNotice('');
    try {
      const response = await apiFetch('/builder/controls', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId, instructions, revision,
          lockedPaths: paths.split('\n').map(path => path.trim()).filter(Boolean) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Unable to save AI controls.');
      setRevision(data.revision); setInstructions(data.instructions); setPaths(data.lockedPaths.join('\n'));
      setNotice('AI controls saved.');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Unable to save AI controls.'); }
    finally { setSaving(false); }
  }

  return <div className="mb-3 space-y-2 text-xs text-white/70">
    <div className="flex items-center justify-between gap-3">
      <label className="flex items-center gap-2">Mode
        <select aria-label="Builder mode" value={mode} disabled={busy} onChange={event => onModeChange(event.target.value as BuilderMode)} className="rounded-lg border border-white/15 bg-zinc-900 px-2 py-2 text-white">
          <option value="build">Build</option><option value="plan">Plan</option><option value="discuss">Discuss</option>
        </select>
      </label>
      <span>{mode === 'build' ? 'Apply changes' : 'No file changes'}</span>
    </div>
    <details className="rounded-lg border border-white/10 p-3">
      <summary className="cursor-pointer">AI instructions &amp; frozen files</summary>
      <div className="mt-3 space-y-3">
        <label className="block">Project instructions
          <textarea aria-label="Project AI instructions" value={instructions} maxLength={4000} rows={4} disabled={!loaded || busy || saving} onChange={event => setInstructions(event.target.value)} placeholder="Keep the existing brand. Preserve working features. Payment processing comes later." className="mt-1 w-full rounded-lg border border-white/15 bg-zinc-900 p-2 text-white" />
        </label>
        <label className="block">Frozen files or folders, one path per line
          <textarea aria-label="Frozen files or folders" value={paths} rows={3} disabled={!loaded || busy || saving} onChange={event => setPaths(event.target.value)} placeholder={'src/components/Header.jsx\nsrc/brand/'} className="mt-1 w-full rounded-lg border border-white/15 bg-zinc-900 p-2 font-mono text-white" />
        </label>
        <p>Frozen paths are blocked from AI writes. End a folder path with /.</p>
        <div className="flex gap-3">
          <button type="button" disabled={!loaded || busy || saving} onClick={() => void save()} className="rounded-lg bg-blue-600 px-3 py-2 text-white disabled:opacity-40">{saving ? 'Saving…' : 'Save controls'}</button>
          <button type="button" disabled={busy || saving} onClick={() => setReload(value => value + 1)} className="rounded-lg border border-white/20 px-3 py-2">Reload controls</button>
        </div>
        {notice && <p role="status">{notice}</p>}
      </div>
    </details>
  </div>;
}

import { useState } from 'react';
import { apiFetch } from '@/lib/api';

type Version = {id:string;label:string;createdAt:number;files:number};
export function VersionHistory({projectId,busy,onRestored}:{projectId:string;busy:boolean;onRestored:()=>void}) {
  const [versions,setVersions]=useState<Version[]>([]);
  const [selected,setSelected]=useState('');
  const [working,setWorking]=useState(false);
  const [notice,setNotice]=useState('');
  async function load(){
    setWorking(true);setNotice('');
    try{const response=await apiFetch(`/builder/history?projectId=${encodeURIComponent(projectId)}`);
      const data=await response.json();if(!response.ok)throw new Error(data.message);
      setVersions(data.versions);if(!data.versions.length)setNotice('No source versions yet. Your next build saves one automatically.');
    }catch(error){setNotice(error instanceof Error?error.message:'History could not load.');}
    finally{setWorking(false);}
  }
  async function restore(){
    if(!selected||busy||working)return;
    setWorking(true);setNotice('');
    try{const response=await apiFetch('/builder/history',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({projectId,versionId:selected})});
      const data=await response.json();if(!response.ok)throw new Error(data.message);
      setNotice(data.message);setSelected('');onRestored();
    }catch(error){setNotice(error instanceof Error?error.message:'Restore failed.');}
    finally{setWorking(false);}
  }
  return <details className="mb-3 rounded-lg border border-white/10 p-3 text-xs text-slate-300">
    <summary className="cursor-pointer">Source version history</summary>
    <p className="mt-2">Restore code from an earlier build. Your current source is backed up first. Publishing requires fresh verification.</p>
    <button type="button" disabled={busy||working} onClick={()=>void load()} className="my-2 rounded-lg border border-white/20 px-3 py-2">Refresh versions</button>
    {!!versions.length&&<select aria-label="Source version" value={selected} disabled={busy||working} onChange={event=>setSelected(event.target.value)} className="block w-full rounded-lg bg-zinc-900 p-2 text-white">
      <option value="">Choose a source version</option>{versions.map(version=><option key={version.id} value={version.id}>{new Date(version.createdAt*1000).toLocaleString()} — {version.label} ({version.files} files)</option>)}
    </select>}
    {selected&&<div className="mt-2"><p>Replace current source with this version? The live published site will stay as it is.</p><button type="button" disabled={busy||working} onClick={()=>void restore()} className="mt-2 rounded-lg bg-blue-600 px-3 py-2 text-white">Back up current source and restore</button></div>}
    {notice&&<p role="status" className="mt-2">{notice}</p>}
  </details>;
}

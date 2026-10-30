import {useState} from 'react';
import {apiFetch} from '@/lib/api';
export function AppBackend({projectId,busy,onConfigured}:{projectId:string;busy:boolean;onConfigured:()=>void}){
 const [url,setUrl]=useState('');const [key,setKey]=useState('');const [working,setWorking]=useState(false);const [notice,setNotice]=useState('');
 async function connect(){
  setWorking(true);setNotice('');
  try{const response=await apiFetch('/builder/app-backend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({projectId,url,publishableKey:key})});
   const data=await response.json();if(!response.ok)throw new Error(data.message);
   setKey('');setNotice(data.message);onConfigured();
  }catch(error){setNotice(error instanceof Error?error.message:'Connection setup failed.');}finally{setWorking(false);}
 }
 return <details className="mb-3 rounded-lg border border-white/10 p-3 text-xs text-slate-300"><summary className="cursor-pointer">App database, authentication &amp; storage</summary>
  <p className="mt-2">Connect this app to its own Supabase project. Setup installs a client; ask Genesys to implement and test your app flows afterward. Use only a public publishable key.</p>
  <label className="mt-2 block">App Supabase URL<input aria-label="App Supabase URL" type="url" value={url} disabled={busy||working} onChange={e=>setUrl(e.target.value)} placeholder="https://your-project.supabase.co" className="mt-1 w-full rounded bg-zinc-900 p-2"/></label>
  <label className="mt-2 block">Publishable key<input aria-label="App publishable key" value={key} disabled={busy||working} onChange={e=>setKey(e.target.value)} autoComplete="off" placeholder="sb_publishable_…" className="mt-1 w-full rounded bg-zinc-900 p-2"/></label>
  <button type="button" disabled={busy||working||!url||!key} onClick={()=>void connect()} className="mt-3 rounded bg-blue-600 px-3 py-2 text-white">{working?'Configuring…':'Configure app backend'}</button>
  {notice&&<p role="status" className="mt-2">{notice}</p>}
 </details>;
}

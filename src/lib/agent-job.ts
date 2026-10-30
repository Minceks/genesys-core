import { apiFetch } from './api';
type Mode = 'build' | 'plan' | 'discuss';
export type PendingJob = { jobId: string; prompt: string; mode: Mode };
const key = (project: string) => `genesys_pending_${project}`;
export function pendingJob(project: string): PendingJob | null {
  try { const job = JSON.parse(sessionStorage.getItem(key(project)) || 'null'); return job && typeof job.jobId === 'string' && typeof job.prompt === 'string' ? job : null; }
  catch { return null; }
}
function save(project: string, job: PendingJob | null) {
  try { if (job) sessionStorage.setItem(key(project), JSON.stringify(job)); else sessionStorage.removeItem(key(project)); } catch { /* Polling still works if storage is unavailable. */ }
}
export async function runAgentJob(project: string, prompt: string, options: { mode?: Mode; history?: { role: string; content: string }[]; onProgress?: (stage: string) => void }) {
  let job = pendingJob(project);
  if (job && (job.prompt !== prompt || job.mode !== (options.mode || 'build'))) throw new Error('Reconnect your saved request before submitting a different request.');
  if (!job) {
    const response = await apiFetch('/agent/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId: project, prompt, mode: options.mode, history: options.history?.slice(-10) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || `Could not start request (${response.status}).`);
    if (typeof data.jobId !== 'string') throw new Error('The server did not return a saved request ID.');
    job = { jobId: data.jobId, prompt, mode: options.mode || 'build' }; save(project, job);
  }
  const deadline = Date.now() + 20 * 60 * 1000;
  let failures = 0;
  while (Date.now() < deadline) {
    let response: Response;
    try { response = await apiFetch(`/agent/jobs/${encodeURIComponent(job.jobId)}?projectId=${encodeURIComponent(project)}`); failures = 0; }
    catch { if (++failures >= 3) throw new Error('Connection interrupted. Your request remains saved; reconnect to continue watching it.'); await new Promise(resolve => setTimeout(resolve, 3000)); continue; }
    const data = await response.json();
    if (!response.ok) { if (response.status === 404) save(project, null); throw new Error(data.message || `Could not reconnect (${response.status}).`); }
    options.onProgress?.(data.stage || 'Working');
    if (data.state === 'completed' || data.state === 'failed') {
      save(project, null); return data.result || { status: 'error', message: 'The saved request finished without a result.' };
    }
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  throw new Error('This request is still running on the server. Reconnect to its saved progress.');
}

import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../lib/api';
import { Rocket } from 'lucide-react';

export type PublicationCandidate = { checkpointId: string; promotionToken: string };
type ReleaseReview = { status: 'blocked' | 'needs_review'; reviewHash: string;
  visualAssessment: string; blockers: string[];
  acknowledgements: { id: string; label: string; items: string[] }[] };

function readReview(value: unknown): ReleaseReview {
  const data = value as ReleaseReview | null;
  const strings = (items: unknown): items is string[] => Array.isArray(items) && items.every(item => typeof item === 'string');
  if (!data || !['blocked', 'needs_review'].includes(data.status) || typeof data.reviewHash !== 'string'
    || typeof data.visualAssessment !== 'string' || !strings(data.blockers) || !Array.isArray(data.acknowledgements)
    || !data.acknowledgements.every(item => item && typeof item.id === 'string' && typeof item.label === 'string' && strings(item.items))) {
    throw new Error('Release checks were incomplete. Please retry.');
  }
  return data;
}

export function PublishProject({ projectId, candidate, busy }: {
  projectId: string; candidate: PublicationCandidate | null; busy: boolean;
}) {
  const [review, setReview] = useState<ReleaseReview | null>(null);
  const [accepted, setAccepted] = useState<string[]>([]);
  const [checking, setChecking] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [notice, setNotice] = useState('');
  const [url, setUrl] = useState('');
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    else if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);

  async function loadReview(signal?: AbortSignal) {
    if (!candidate || busy) return;
    setChecking(true); setNotice(''); setReview(null); setAccepted([]);
    try {
      const response = await apiFetch('/publish/review', { method: 'POST', signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ projectId, ...candidate }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Release checks could not load.');
      const nextReview = readReview(data);
      if (!signal?.aborted) setReview(nextReview);
    } catch (error) {
      if (!signal?.aborted) setNotice(error instanceof Error ? error.message : 'Release checks could not load.');
    } finally { if (!signal?.aborted) setChecking(false); }
  }

  useEffect(() => {
    const controller = new AbortController();
    setReview(null); setAccepted([]); setUrl(''); setNotice(''); setChecking(false);
    if (candidate && !busy) void loadReview(controller.signal);
    return () => controller.abort();
  }, [projectId, candidate?.checkpointId, candidate?.promotionToken, busy]);

  const reviewed = !!review && review.status !== 'blocked'
    && review.acknowledgements.every(item => accepted.includes(item.id));

  async function publish() {
    if (!candidate || !review || !reviewed || busy || checking || publishing) return;
    setPublishing(true); setNotice('');
    try {
      const response = await apiFetch('/publish', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId, ...candidate, reviewHash: review.reviewHash, acknowledgements: accepted }),
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 428) { setAccepted([]); setReview(data.review ? readReview(data.review) : null); }
        throw new Error(data.message || 'Publishing could not complete. Your verified preview is preserved.');
      }
      const parsed = new URL(data.url);
      if (parsed.protocol !== 'https:' || parsed.username || parsed.password) throw new Error('The server returned an invalid publication address.');
      setUrl(parsed.href); setNotice('Published. Your website is available at the link below.');
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Publishing could not complete.');
    } finally { setPublishing(false); }
  }

  return <>
    <button type="button" onClick={() => setOpen(true)} className="g-btn g-btn-primary g-btn-sm" aria-label="Publish website"><Rocket size={15} /><span className="g-btn-label">Publish</span></button>
    <dialog ref={dialog} onCancel={() => setOpen(false)} onClose={() => setOpen(false)} aria-labelledby="publication-review-title"
      style={{ width: 'min(620px, calc(100vw - 32px))', maxHeight: '85dvh' }}
      className="m-auto overflow-y-auto rounded-2xl border border-white/20 bg-[var(--surface)] p-0 text-sm text-slate-200 shadow-2xl backdrop:bg-black/75">
    <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-[var(--surface)] px-5 py-4">
      <h2 id="publication-review-title" className="text-lg font-semibold text-white">Review and publish</h2>
      <button type="button" autoFocus aria-label="Close publishing review" onClick={() => setOpen(false)} className="min-h-11 rounded-lg border border-white/20 px-3">Close</button>
    </div>
    <div className="p-5">
    <p className="mt-3 leading-relaxed">Review this version’s design checks and integration limits before making it public.</p>
    {!candidate ? <p className="mt-2 text-amber-200">Complete a successful build and browser verification to prepare this version for publishing.</p> : <>
      {checking && <p role="status" className="mt-3">Loading release checks…</p>}
      {review && <div className="mt-3 space-y-3">
        <p className={review.status === 'blocked' ? 'font-medium text-red-200' : 'font-medium text-sky-200'}>
          {review.status === 'blocked' ? 'Fix these issues before publishing' : 'Ready for your release review'}
        </p>
        {review.blockers.length > 0 && <ul className="list-disc space-y-2 pl-5 text-red-200">{review.blockers.map((item, index) => <li key={index}>{item}</li>)}</ul>}
        <p>Visual review: {review.visualAssessment === 'ready' ? 'No major issues reported in the captured screens.' : review.visualAssessment === 'needs_polish' ? 'Repairs required.' : 'Your desktop and phone review is required.'}</p>
        {review.acknowledgements.map(item => <div key={item.id} className={item.id === 'deferred-integrations' ? 'rounded-lg border border-amber-400/30 bg-amber-950/20 p-3' : ''}>
          {item.items.length > 0 && <ul className="mb-2 list-disc space-y-2 pl-5 text-slate-200">{item.items.map((text, index) => <li key={index}>{text}</li>)}</ul>}
          <label className="flex items-start gap-2 leading-relaxed">
            <input type="checkbox" checked={accepted.includes(item.id)} disabled={review.status === 'blocked' || busy || publishing || checking}
              onChange={event => setAccepted(previous => event.target.checked ? [...previous, item.id] : previous.filter(id => id !== item.id))} className="mt-1 shrink-0" />
            {item.label}
          </label>
        </div>)}
      </div>}
      <button type="button" disabled={busy || publishing || checking} onClick={() => void loadReview()} className="mt-4 min-h-11 w-full rounded-lg border border-white/20 px-3 py-2 disabled:opacity-40 sm:w-auto">Refresh release checks</button>
      <button type="button" disabled={!reviewed || busy || publishing || checking} onClick={() => void publish()} className="mt-3 min-h-11 w-full rounded-lg bg-[var(--accent)] px-4 py-2 font-medium text-white disabled:opacity-40 sm:ml-2 sm:w-auto">
        {publishing ? 'Publishing…' : url ? 'Publish this version again' : 'Publish verified version'}
      </button>
    </>}
    {notice && <p role="status" className="mt-3 leading-relaxed">{notice}</p>}
    {url && <a href={url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-blue-300 underline">Open published website</a>}
    </div>
    </dialog>
  </>;
}

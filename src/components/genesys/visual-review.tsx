import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

type Review = { id: string; createdAt: number; issues: string[]; suggestions: string[] };
export function VisualReview({ projectId, busy }: { projectId: string; busy: boolean }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [selected, setSelected] = useState(0);
  const [images, setImages] = useState<string[]>([]);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    if (busy) return;
    let active = true;
    apiFetch(`/builder/reviews?projectId=${encodeURIComponent(projectId)}`)
      .then(async response => { if (!response.ok) throw new Error('Visual review could not load.'); return response.json(); })
      .then(data => { if (active) { setReviews(data.reviews || []); setSelected(0); setNotice(''); } })
      .catch(error => { if (active) setNotice(error.message); });
    return () => { active = false; };
  }, [projectId, busy]);
  const review = reviews[selected];
  useEffect(() => {
    let active = true;
    const urls: string[] = [];
    setImages([]);
    if (review) Promise.all(['desktop', 'phone'].map(async viewport => {
      const response = await apiFetch(`/builder/reviews/${review.id}/${viewport}?projectId=${encodeURIComponent(projectId)}`);
      if (!response.ok) throw new Error('Review image unavailable.');
      const url = URL.createObjectURL(await response.blob());
      if (!active) URL.revokeObjectURL(url); else urls.push(url);
      return url;
    })).then(result => { if (active) setImages(result); }).catch(error => { if (active) setNotice(error.message); });
    return () => { active = false; urls.forEach(url => URL.revokeObjectURL(url)); };
  }, [review?.id, projectId]);
  return <details className="border border-white/10 rounded-xl p-3 text-xs text-white/70">
    <summary className="cursor-pointer font-medium">Desktop and phone review</summary>
    <p className="mt-2 text-white/40">Screenshots and layout findings. Visual taste still needs review.</p>
    {reviews.length > 1 && <select aria-label="Review version" className="mt-2 bg-zinc-900 p-2 rounded" value={selected} onChange={event => setSelected(Number(event.target.value))}>
      {reviews.map((item, index) => <option key={item.id} value={index}>{index === 0 ? 'Latest' : 'Previous'} — {new Date(item.createdAt).toLocaleString()}</option>)}
    </select>}
    {images.length === 2 && <div className="grid grid-cols-2 gap-2 mt-3">{images.map((url, index) => <a key={url} href={url} target="_blank" rel="noreferrer"><img src={url} alt={`${index ? 'Phone' : 'Desktop'} build screenshot`} className="rounded border border-white/10 max-h-52 w-full object-contain object-top" /><span>{index ? 'Phone' : 'Desktop'}</span></a>)}</div>}
    {review && <ul className="mt-2 space-y-1">{[...review.issues, ...review.suggestions].map((item, index) => <li key={index}>{item}</li>)}</ul>}
    {!review && !notice && <p className="mt-2">Evidence appears after the next layout review.</p>}
    {notice && <p role="status" className="mt-2">{notice}</p>}
  </details>;
}

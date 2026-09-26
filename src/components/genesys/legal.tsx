import React from 'react';

interface LegalProps {
  title: string;
  subtitle: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPage({ title, subtitle, lastUpdated, children }: LegalProps) {
  return (
    <div className="min-h-screen bg-black text-zinc-300 pt-32 pb-20 px-6 font-sans">
      <div className="max-w-3xl mx-auto">
        <header className="mb-16 border-b border-white/10 pb-10">
          <h1 className="text-5xl font-bold text-white mb-4" style={{ fontFamily: 'Sora' }}>{title}</h1>
          <p className="text-blue-400 font-medium">{subtitle}</p>
          <p className="text-xs text-zinc-500 mt-4 uppercase tracking-widest">Last Updated: {lastUpdated}</p>
        </header>
        <div className="space-y-12 leading-relaxed text-sm">
          {children}
        </div>
      </div>
    </div>
  );
}

export function LegalSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-xl font-bold text-white mb-4" style={{ fontFamily: 'Sora' }}>{title}</h2>
      <div className="space-y-4">
        {children}
      </div>
    </section>
  );
}

// --- THE FIX: This alias prevents the "No matching export" error ---
export { LegalPage as LegalReader };
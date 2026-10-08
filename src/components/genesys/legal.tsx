import React from 'react';

interface LegalProps {
  title: string;
  subtitle: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPage({ title, subtitle, lastUpdated, children }: LegalProps) {
  return (
    <div className="min-h-screen bg-slate-50 px-5 pb-20 pt-12 text-slate-700 sm:px-8 sm:pt-16">
      <div className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-10">
        <header className="mb-10 border-b border-slate-100 pb-8">
          <h1 className="mb-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">{title}</h1>
          <p className="font-medium text-blue-700">{subtitle}</p>
          <p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">Last updated: {lastUpdated}</p>
        </header>
        <div className="space-y-10 text-sm leading-7">
          {children}
        </div>
      </div>
    </div>
  );
}

export function LegalSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold tracking-tight text-slate-900">{title}</h2>
      <div className="space-y-4">
        {children}
      </div>
    </section>
  );
}

// --- THE FIX: This alias prevents the "No matching export" error ---
export { LegalPage as LegalReader };

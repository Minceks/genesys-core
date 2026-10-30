import React from 'react';
import { Navbar } from './navbar';
import { Footer } from './footer';

interface LegalProps {
  title: string;
  subtitle: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPage({ title, subtitle, lastUpdated, children }: LegalProps) {
  return (
    <div className="g-page text-[var(--muted)]">
      <Navbar />
      <div className="max-w-3xl mx-auto px-6 py-16">
        <header className="mb-16 border-b border-white/10 pb-10">
          <h1 className="text-4xl font-extrabold text-[var(--text)] sm:text-5xl mb-4">{title}</h1>
          <p className="text-[var(--accent-text)] font-medium">{subtitle}</p>
          <p className="text-xs text-[var(--faint)] mt-4">Last Updated: {lastUpdated}</p>
        </header>
        <div className="space-y-12 leading-relaxed text-sm">
          {children}
        </div>
      </div>
      <Footer />
    </div>
  );
}

export function LegalSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-xl font-bold text-[var(--text)] mb-4">{title}</h2>
      <div className="space-y-4">
        {children}
      </div>
    </section>
  );
}

// --- THE FIX: This alias prevents the "No matching export" error ---
export { LegalPage as LegalReader };
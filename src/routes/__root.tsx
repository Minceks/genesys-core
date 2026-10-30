import { createRootRoute, Outlet, HeadContent, Scripts, Link } from '@tanstack/react-router';
import React from 'react';
import { RecoveryRedirect } from '../lib/recovery-redirect';

export const Route = createRootRoute({
  notFoundComponent: () => (
    <main className="g-page g-glow grid place-items-center px-6 text-center">
      <div className="max-w-md">
        <p className="g-eyebrow">404</p>
        <h1 className="mt-3 text-4xl font-extrabold">Page not found</h1>
        <p className="mt-4 text-[var(--muted)]">This address is not available. Return home or open your projects.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/" className="g-btn g-btn-secondary">Home</Link>
          <Link to="/account" className="g-btn g-btn-primary">Your projects</Link>
        </div>
      </div>
    </main>
  ),
  component: () => (
    <React.Fragment>
      <HeadContent />
      <RecoveryRedirect />
      <div className="min-h-screen">
        <Outlet /> 
      </div>
      <Scripts />
    </React.Fragment>
  ),
});

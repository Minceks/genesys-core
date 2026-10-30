import { createRootRoute, Outlet, HeadContent, Scripts, Link } from '@tanstack/react-router';
import React from 'react';
import { RecoveryRedirect } from '../lib/recovery-redirect';

export const Route = createRootRoute({
  notFoundComponent: () => <main className="min-h-screen bg-[#080b12] px-6 py-24 text-slate-100"><div className="mx-auto max-w-xl"><p className="text-blue-300">404</p><h1 className="mt-4 text-4xl font-semibold">Page not found</h1><p className="mt-5 text-slate-400">This address is not available. Return home or open your projects.</p><Link to="/" className="mt-7 inline-flex min-h-12 items-center rounded-xl bg-blue-500 px-5 text-white">Back to home</Link><Link to="/account" className="ml-5 inline-flex min-h-12 items-center">Your projects</Link></div></main>,
  component: () => (
    <React.Fragment>
      <HeadContent />
      <RecoveryRedirect />
      <div className="min-h-screen bg-black text-white">
        <Outlet /> 
      </div>
      <Scripts />
    </React.Fragment>
  ),
});

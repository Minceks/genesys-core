import { createRootRoute, Outlet, HeadContent, Scripts } from '@tanstack/react-router';
import React from 'react';

export const Route = createRootRoute({
  component: () => (
    <React.Fragment>
      <HeadContent />
      <div className="min-h-screen bg-black text-white">
        <Outlet /> 
      </div>
      <Scripts />
    </React.Fragment>
  ),
});
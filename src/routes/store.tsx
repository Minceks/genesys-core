import { createRoute } from '@tanstack/react-router';
import { Route as rootRoute } from './__root';
import React from 'react';
import { StoreUI } from '../components/store/StoreUI';

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/store',
  component: () => (
    <div className='min-h-screen bg-black text-white pt-24'>
      <h1 className='text-center text-6xl font-bold mb-12'>
        LUXURY <span className='text-blue-500'>CORE</span>
      </h1>
      <StoreUI />
    </div>
  ),
});
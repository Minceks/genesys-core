import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <div style={{padding: '50px', background: 'black', color: '#00d9ff', height: '100vh'}}><h1>GENESYS HOME LIVE</h1></div>,
})
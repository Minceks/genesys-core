import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/p/$projectId',
  component: () => <div style={{padding: '50px', background: 'black', color: 'white', height: '100vh'}}><h1>PROJECT VIEWER LIVE</h1></div>,
})
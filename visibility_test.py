import os

base = os.path.join(os.getcwd(), "genesys-pro")
src = os.path.join(base, "src")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Set: {path}")

# 1. ROOT
write(os.path.join(src, "routes", "__root.tsx"), """
import { Outlet } from '@tanstack/react-router'
import React from 'react'
export const Route = { component: () => <Outlet /> }
""")

# 2. HOME PAGE (RED)
write(os.path.join(src, "routes", "index.tsx"), """
import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'
export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <div style={{background: 'red', height: '100vh', padding: '50px'}}><h1>THIS IS THE HOME PAGE (RED)</h1><a href="/build" style={{color: 'white'}}>Go to Builder</a></div>
})
""")

# 3. BUILD PAGE (BLUE)
write(os.path.join(src, "routes", "build.tsx"), """
import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'
export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/build',
  component: () => <div style={{background: 'blue', height: '100vh', padding: '50px'}}><h1>THIS IS THE BUILDER (BLUE)</h1><a href="/" style={{color: 'white'}}>Go Home</a></div>
})
""")

# 4. MAP
write(os.path.join(src, "routeTree.gen.ts"), """
import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'
import { Route as buildRoute } from './routes/build'
export const routeTree = rootRoute.addChildren([indexRoute, buildRoute])
""")
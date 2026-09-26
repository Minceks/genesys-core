import os
import shutil

base = os.path.join(os.getcwd(), "genesys-pro")
src = os.path.join(base, "src")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Repaired: {path}")

# 1. THE ROOT (Corrected with createRootRoute)
write(os.path.join(src, "routes", "__root.tsx"), """
import { createRootRoute, Outlet } from '@tanstack/react-router'
import React from 'react'

export const Route = createRootRoute({
  component: () => (
    <div id="root-container">
      <Outlet />
    </div>
  ),
})
""")

# 2. THE HOME PAGE (Minimalist)
write(os.path.join(src, "routes", "index.tsx"), """
import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <div style={{background: 'red', height: '100vh', padding: '50px', color: 'white'}}><h1>RED HOME PAGE IS LIVE</h1></div>,
})
""")

# 3. THE BUILDER PAGE (Minimalist)
write(os.path.join(src, "routes", "build.tsx"), """
import { createRoute } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import React from 'react'

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: '/build',
  component: () => <div style={{background: 'blue', height: '100vh', padding: '50px', color: 'white'}}><h1>BLUE BUILDER IS LIVE</h1></div>,
})
""")

# 4. THE ROUTE TREE (The fix for the Duplicate error)
write(os.path.join(src, "routeTree.gen.ts"), """
import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'
import { Route as buildRoute } from './routes/build'

export const routeTree = rootRoute.addChildren([
  indexRoute,
  buildRoute,
])
""")

# 5. THE MAIN ENTRY
write(os.path.join(src, "main.tsx"), """
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

const router = createRouter({ routeTree })

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
""")

# 6. NUKE CACHE
cache = os.path.join(base, "node_modules", ".vite")
if os.path.exists(cache):
    shutil.rmtree(cache)
    print("🧹 Vite Cache Nuked")
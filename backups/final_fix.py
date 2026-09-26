import os

# Set paths
base = os.path.join(os.getcwd(), "genesys-pro")
src = os.path.join(base, "src")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Reconstructed: {os.path.basename(path)}")

# 1. THE ROOT SKELETON
root_tsx = """
import { createRootRoute, Outlet } from '@tanstack/react-router'
import React from 'react'

export const Route = createRootRoute({
  component: () => (
    <div style={{ margin: 0, padding: 0, background: '#050505', minHeight: '100vh', color: 'white' }}>
      <Outlet />
    </div>
  ),
})
"""

# 2. THE HOME PAGE
index_tsx = """
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/')({
  component: () => (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h1 style={{ color: '#00d9ff', fontSize: '4rem', fontFamily: 'sans-serif' }}>GENE-SYS ONLINE</h1>
    </div>
  ),
})
"""

# 3. THE ROUTE TREE (The fix for the Duplicate error)
tree_ts = """
import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'

export const routeTree = rootRoute.addChildren([
  indexRoute,
])
"""

# 4. THE IGNITION
main_tsx = """
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

const router = createRouter({ routeTree })

const rootElement = document.getElementById('root')!
if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(<RouterProvider router={router} />)
}
"""

write(os.path.join(src, "routes", "__root.tsx"), root_tsx)
write(os.path.join(src, "routes", "index.tsx"), index_tsx)
write(os.path.join(src, "routeTree.gen.ts"), tree_ts)
write(os.path.join(src, "main.tsx"), main_tsx)

print("\n🚀 SURGERY COMPLETE! Restart your server.")
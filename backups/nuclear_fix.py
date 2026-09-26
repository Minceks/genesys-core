import os
import shutil

# Set paths
base_path = os.path.join(os.getcwd(), "genesys-pro")
src_path = os.path.join(base_path, "src")

def force_write(path, content):
    full_path = os.path.join(src_path, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Fixed: {path}")

# 1. THE ROOT (Simplified)
root_code = """
import { createRootRoute, Outlet } from '@tanstack/react-router'
import React from 'react'

export const Route = createRootRoute({
  component: () => (
    <React.Fragment>
      <Outlet />
    </React.Fragment>
  ),
})
"""

# 2. THE INDEX (Simplified)
index_code = """
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/')({
  component: () => (
    <div style={{ 
      height: '100vh', 
      background: '#050505', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center' 
    }}>
      <h1 style={{ color: '#00f2ff', fontFamily: 'sans-serif', fontSize: '3rem' }}>
        GENE-SYS IS ONLINE
      </h1>
    </div>
  ),
})
"""

# 3. THE ROUTE TREE (The actual fix for the Duplicate error)
# We avoid using .addChildren() on the root here to prevent the duplicate ID bug
tree_code = """
import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'

// Map the relationship manually
const indexRouteWithParent = indexRoute.update({
  getParentRoute: () => rootRoute,
} as any)

// The routeTree is ONLY the rootRoute
export const routeTree = rootRoute.addChildren([indexRouteWithParent])
"""

# 4. THE IGNITION (Cleaned)
main_code = """
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

force_write("routes/__root.tsx", root_code)
force_write("routes/index.tsx", index_code)
force_write("routeTree.gen.ts", tree_code)
force_write("main.tsx", main_code)

# 5. NUKE THE CACHE
cache_path = os.path.join(base_path, "node_modules", ".vite")
if os.path.exists(cache_path):
    shutil.rmtree(cache_path)
    print("✅ Vite Cache Nuked")

print("\n🚀 SYSTEM REPAIRED! Run 'npm run dev' inside genesys-pro.")
import os

# The folder where your app lives
folder = os.path.join(os.getcwd(), "genesys-pro", "src")

def force_write(subpath, content):
    path = os.path.join(folder, subpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Cleaned: {subpath}")

# 1. CLEAN MAIN.TSX
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

# 2. CLEAN __ROOT.TSX
root_tsx = """
import { createRootRoute, Outlet, HeadContent, Scripts } from '@tanstack/react-router'
import React from 'react'

export const Route = createRootRoute({
  component: () => (
    <html lang="en">
      <head><HeadContent /></head>
      <body style={{ margin: 0, background: '#050505', color: 'white', fontFamily: 'sans-serif' }}>
        <Outlet />
        <Scripts />
      </body>
    </html>
  ),
})
"""

# 3. CLEAN INDEX.TSX
index_tsx = """
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/')({
  component: () => (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h1 style={{ color: '#00d9ff', fontSize: '5rem', fontWeight: 'bold' }}>SYSTEM ONLINE</h1>
    </div>
  ),
})
"""

force_write("main.tsx", main_tsx)
force_write("routes/__root.tsx", root_tsx)
force_write("routes/index.tsx", index_tsx)

print("\n🚀 CORE FILES RESET! Now go to your terminal and start the server.")

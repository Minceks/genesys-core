import os

# Ensure we are targeting the right folder
base_path = os.path.join(os.getcwd(), "genesys-pro")
src_path = os.path.join(base_path, "src")

def force_write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Repaired: {path}")

# 1. FIX INDEX.HTML (The Front Door)
index_html = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Genesys AI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

# 2. FIX MAIN.TSX (The Engine)
main_tsx = """
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'
import './styles.css'

const router = createRouter({ routeTree })

const rootElement = document.getElementById('root')!
if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(<RouterProvider router={router} />)
}
"""

# 3. FIX ROUTETREE (The Map)
# We only include the 2 pages we are 100% sure exist
route_tree = """
import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'
import { Route as buildRoute } from './routes/build'

export const routeTree = rootRoute.addChildren([
  indexRoute,
  buildRoute,
])
"""

# 4. FIX __ROOT.TSX (The Skeleton)
root_tsx = """
import { createRootRoute, Outlet, HeadContent, Scripts } from '@tanstack/react-router'
import React from 'react'

export const Route = createRootRoute({
  component: () => (
    <React.Fragment>
      <HeadContent />
      <Outlet />
      <Scripts />
    </React.Fragment>
  ),
})
"""

force_write(os.path.join(base_path, "index.html"), index_html)
force_write(os.path.join(src_path, "main.tsx"), main_tsx)
force_write(os.path.join(src_path, "routeTree.gen.ts"), route_tree)
force_write(os.path.join(src_path, "routes", "__root.tsx"), root_tsx)

print("\n🚀 CORE REPAIR COMPLETE. Restart your server now.")
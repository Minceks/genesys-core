"""Minimal, independent application files for user-owned projects."""

import json
from .persistence import PERSISTENT_STATE_SOURCE
from .design_foundation import PLACEHOLDER

STARTER_FILES = {
    "src/usePersistentState.js": PERSISTENT_STATE_SOURCE,
    "package.json": json.dumps({
        "name": "user-project", "private": True, "version": "0.0.0",
        "type": "module",
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
        "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
        "devDependencies": {"vite": "^6.4.3", "@vitejs/plugin-react": "^4.4.0"},
    }, indent=2) + "\n",
    "index.html": '<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Your project</title><link rel="icon" type="image/svg+xml" href="/favicon.svg"></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>\n',
    "public/favicon.svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><!-- Replace this neutral mark with the project identity. --><rect width="64" height="64" rx="16" fill="#252525"/><path d="M18 18h12v12H18zm16 0h12v12H34zM18 34h12v12H18zm16 0h12v12H34z" fill="#f7f7f5"/></svg>\n',
    "vite.config.js": "import { defineConfig } from 'vite'\nimport react from '@vitejs/plugin-react'\nexport default defineConfig({ plugins: [react()] })\n",
    "src/main.jsx": "import React from 'react'\nimport { createRoot } from 'react-dom/client'\nimport App from './App'\nimport './foundation.css'\nimport './design-tokens.css'\nimport './styles.css'\ncreateRoot(document.getElementById('root')).render(<App />)\n",
    "src/design-tokens.css": PLACEHOLDER,
    "src/foundation.css": "/* Responsive defaults; project styles choose the visual identity. */\n*, *::before, *::after { box-sizing: border-box; } body { margin: 0; } #root { width: 100%; min-height: 100dvh; min-width: 0; } img, video, canvas, svg { max-width: 100%; } img, video { height: auto; } button, input, select, textarea { font: inherit; } input, select, textarea { max-width: 100%; } main, section, article, aside, form { min-width: 0; } figure { margin: 0; } p { overflow-wrap: anywhere; } button, a { touch-action: manipulation; }\n",
    "src/App.jsx": "export default function App() { return <main><h1>Your project is ready</h1><p>Describe what you want to build in the chat.</p></main> }\n",
    "src/styles.css": "/* Project composition: reuse design-tokens.css and implement the chosen page layouts here. */\n",
    ".gitignore": "node_modules/\ndist/\n.env\n.env.*\n",
    "PROJECT.md": "This is an independent user application. Implement requested UI in src/App.jsx and show it at /. recovered/ contains reference-only backups: NEVER import these files into the app. Read them and rewrite relevant functionality as standalone components under src/. Remove GeneSys routing, platform navigation and platform component imports. Never recreate the GeneSys platform here.\n",
    ".genesys-user-project": "1\n",
}

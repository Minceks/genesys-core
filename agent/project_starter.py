"""Minimal, independent application files for user-owned projects."""

import json

STARTER_FILES = {
    "package.json": json.dumps({
        "name": "user-project", "private": True, "version": "0.0.0",
        "type": "module",
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
        "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
        "devDependencies": {"vite": "^6.4.3", "@vitejs/plugin-react": "^4.4.0"},
    }, indent=2) + "\n",
    "index.html": '<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Your project</title></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>\n',
    "vite.config.js": "import { defineConfig } from 'vite'\nimport react from '@vitejs/plugin-react'\nexport default defineConfig({ plugins: [react()] })\n",
    "src/main.jsx": "import React from 'react'\nimport { createRoot } from 'react-dom/client'\nimport App from './App'\nimport './styles.css'\ncreateRoot(document.getElementById('root')).render(<App />)\n",
    "src/App.jsx": "export default function App() { return <main><h1>Your project is ready</h1><p>Describe what you want to build in the chat.</p></main> }\n",
    "src/styles.css": "* { box-sizing: border-box; } body { margin: 0; font-family: system-ui, sans-serif; color: #172554; background: #f8fafc; } main { max-width: 960px; margin: 80px auto; padding: 24px; }\n",
    ".gitignore": "node_modules/\ndist/\n.env\n.env.*\n",
    "PROJECT.md": "This is an independent user application. Implement requested UI in src/App.jsx and show it at /. Files under recovered/ are preserved edits from the previous workspace; read and adapt them when relevant. Never recreate the GeneSys platform here.\n",
    ".genesys-user-project": "1\n",
}

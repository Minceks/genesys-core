import os

# Define the base project path
base_path = os.path.join(os.getcwd(), "genesys-pro")

def write_file(filename, content):
    full_path = os.path.join(base_path, filename)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Fixed: {filename}")

# 1. The Vite Config (THE FIX FOR YOUR ERROR)
vite_code = """
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    tsconfigPaths(),
  ],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
});
"""

# 2. The Package JSON
package_code = """
{
  "name": "genesys-ai-independent",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.475.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "@tanstack/react-router": "latest",
    "@supabase/supabase-js": "latest",
    "vite-tsconfig-paths": "latest",
    "class-variance-authority": "latest",
    "tailwind-merge": "latest",
    "clsx": "latest"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.0.0"
  }
}
"""

write_file("vite.config.ts", vite_code)
write_file("package.json", package_code)

print("\n🚀 Project files repaired! Now run 'npm install' inside the genesys-pro folder.")
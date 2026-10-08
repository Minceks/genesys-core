import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    tsconfigPaths(),
  ],
  resolve: {
    alias: {
      "@": "/src", // <--- THIS LINE ALLOWS THE @/ IMPORTS TO WORK
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("/node_modules/chart.js/") || id.includes("/node_modules/react-chartjs-2/")) {
            return "charts";
          }

          if (
            id.includes("/node_modules/react-markdown/") ||
            id.includes("/node_modules/remark-gfm/") ||
            id.includes("/node_modules/remark-parse/") ||
            id.includes("/node_modules/remark-rehype/") ||
            id.includes("/node_modules/rehype-") ||
            id.includes("/node_modules/micromark") ||
            id.includes("/node_modules/mdast-") ||
            id.includes("/node_modules/hast-") ||
            id.includes("/node_modules/unified/")
          ) {
            return "markdown";
          }
        },
      },
    },
  },
})

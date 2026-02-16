import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Target ES2019 so react-snap's bundled Chromium can parse the output
    // (older Chromium doesn't support optional chaining / nullish coalescing)
    target: 'es2019',
  },
})

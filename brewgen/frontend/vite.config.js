import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Build into ../dist so the Flask backend keeps serving the SPA from the same
// place the legacy vue-cli build used (static_folder=../dist/static,
// template_folder=../dist). See brewgen/backend/views.py.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: {
    // In dev, hand API calls to the Flask backend so the SPA can run against a
    // real solver without CORS gymnastics.
    proxy: { '/api': 'http://localhost:5000' }
  },
  build: {
    outDir: '../dist',
    assetsDir: 'static',
    emptyOutDir: true
  },
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.spec.js']
  }
})

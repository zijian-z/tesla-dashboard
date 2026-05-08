import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: process.env.VITE_BASE_PATH ?? '/dashboard/',
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ['recharts'],
          icons: ['lucide-react']
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/dashboard/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/dashboard\/api/, '/api')
      },
      '/dashboard/health': {
        target: 'http://localhost:8000',
        rewrite: () => '/health'
      },
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000'
    }
  }
});

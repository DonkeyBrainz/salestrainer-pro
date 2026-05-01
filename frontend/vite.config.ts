import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      root: '.',
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true
          },
          '/auth/login': {
            target: 'http://localhost:8000',
            changeOrigin: true
          },
          '/auth/callback': {
            target: 'http://localhost:8000',
            changeOrigin: true,
            // Only proxy POST requests, let GET go to React Router
            bypass: (req) => {
              if (req.method === 'GET') {
                return req.url; // Skip proxy, serve from Vite
              }
            }
          },
          '/auth/refresh': {
            target: 'http://localhost:8000',
            changeOrigin: true
          },
          '/auth/logout': {
            target: 'http://localhost:8000',
            changeOrigin: true
          },
          '/auth/me': {
            target: 'http://localhost:8000',
            changeOrigin: true
          },
          '/ws': {
            target: 'ws://localhost:8000',
            ws: true
          },
          '/health': {
            target: 'http://localhost:8000',
            changeOrigin: true
          }
        }
      },
      plugins: [react()],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'import.meta.env.VITE_API_BASE_URL': JSON.stringify(env.VITE_API_BASE_URL || '')
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, './src'),
        }
      }
    };
});

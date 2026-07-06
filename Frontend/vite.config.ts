import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        // POST /api/chat/stream -> POST /query/stream  (AVANT /api/chat)
        '/api/chat/stream': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: () => '/query/stream',
        },
        // POST /api/chat -> POST /query
        '/api/chat': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: () => '/query',
        },
        // POST /api/cache/clear -> POST /cache/clear
        '/api/cache/clear': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: () => '/cache/clear',
        },
        // GET /api/documents -> GET /documents
        '/api/documents': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: () => '/documents',
        },
        // GET /api/files/* -> GET /files/*
        '/api/files': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/files/, '/files'),
        },
        // GET /api/models -> GET /models
        '/api/models': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: () => '/models',
        },
      },
    },
  };
});


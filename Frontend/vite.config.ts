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
          rewrite: (path) => path.replace(/^\/api\/chat\/stream/, '/query/stream'),
        },
        // POST /api/chat -> POST /query
        '/api/chat': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/chat/, '/query'),
        },
        // POST /api/cache/clear -> POST /cache/clear
        '/api/cache/clear': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/cache\/clear/, '/cache/clear'),
        },
        // GET /api/documents -> GET /documents (la query string, ex: search/doc_type/country/sort,
        // doit etre preservee sinon les filtres de la bibliotheque sont silencieusement ignores)
        '/api/documents': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/documents/, '/documents'),
        },
        // GET /api/metadata -> GET /metadata (categories/pays/annees/modeles)
        '/api/metadata': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/metadata/, '/metadata'),
        },
        // GET /api/health -> GET /health
        '/api/health': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/health/, '/health'),
        },
        // GET /api/files/* -> GET /images/* (le backend sert les images extraites sous /images)
        '/api/files': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/files/, '/images'),
        },
        // POST /api/feedback -> POST /feedback (pouce haut/bas sur une reponse du chat)
        '/api/feedback': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/feedback/, '/feedback'),
        },
      },
    },
  };
});


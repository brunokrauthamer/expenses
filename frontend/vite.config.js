import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiProxy = {
    '/api': {
      target: env.BACKEND_PROXY_TARGET?.trim() || 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  };

  return {
    server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy: apiProxy },
    preview: { proxy: apiProxy },
  };
});

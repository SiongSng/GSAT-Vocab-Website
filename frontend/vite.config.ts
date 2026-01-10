import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [
    tailwindcss(),
    sveltekit()
  ],
  server: {
    port: 5173,
    open: true,
    fs: {
      allow: ['..']
    }
  },
  build: {
    target: 'esnext',
    minify: 'esbuild'
  },
  assetsInclude: ['**/*.gz']
});

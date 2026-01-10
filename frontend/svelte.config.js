import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { mdsvex } from 'mdsvex';
import rehypeSlug from 'rehype-slug';
import rehypeAutolinkHeadings from 'rehype-autolink-headings';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  extensions: ['.svelte', '.md'],
  preprocess: [
    vitePreprocess(),
    mdsvex({
      extensions: ['.md'],
      rehypePlugins: [
        rehypeSlug,
        [rehypeAutolinkHeadings, { behavior: 'wrap' }]
      ]
    })
  ],
  compilerOptions: {
    runes: true
  },
  kit: {
    adapter: adapter({
      pages: 'dist',
      assets: 'dist',
      fallback: '404.html',
      precompress: false,
      strict: false
    }),
    paths: {
      base: process.env.GITHUB_ACTIONS ? '/GSAT-Vocab-Website' : ''
    },
    prerender: {
      concurrency: 20,
      handleHttpError: 'warn',
      handleMissingId: 'warn',
      handleUnseenRoutes: 'ignore',
      entries: [
        '*',
        '/blog',
        '/flashcard',
        '/flashcard/session',
        '/quiz',
        '/quiz/session',
        '/stats'
      ]
    },
    alias: {
      $lib: './src/lib',
      $content: './content'
    }
  }
};

export default config;

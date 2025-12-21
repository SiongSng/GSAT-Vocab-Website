import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import path from "path";

const base = process.env.GITHUB_ACTIONS ? "/GSAT-Vocab-Website/" : "/";

export default defineConfig({
  plugins: [
    tailwindcss(),
    svelte(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      includeAssets: [
        "favicon.ico",
        "favicon.svg",
        "favicon-16x16.png",
        "favicon-32x32.png",
        "apple-touch-icon.png",
        "pwa-icon.svg",
        "pwa-192x192.png",
        "pwa-512x512.png",
        "pwa-1024x1024.png",
        "pwa-maskable.svg",
        "og-image.svg",
        "pwa-maskable-192x192.png",
        "pwa-maskable-512x512.png",
        "pwa-maskable-1024x1024.png",
      ],
      manifest: {
        name: "學測高頻單字",
        short_name: "學測單字",
        description:
          "從歷屆學測試題萃取 5000+ 高頻單字，智慧複習排程搭配詞頻統計與字根拆解，備考效率大提升。",
        theme_color: "#f7f7f7",
        background_color: "#f7f7f7",
        display: "standalone",
        orientation: "portrait-primary",
        scope: base,
        start_url: base,
        categories: ["education", "productivity"],
        lang: "zh-TW",
        icons: [
          {
            src: "pwa-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "pwa-1024x1024.png",
            sizes: "1024x1024",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "pwa-maskable-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "maskable",
          },
          {
            src: "pwa-maskable-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
          {
            src: "pwa-maskable-1024x1024.png",
            sizes: "1024x1024",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        globIgnores: ["data/**", "**/kokoro-*.js"],
      },
    }),
  ],
  base,
  resolve: {
    alias: {
      $lib: path.resolve(__dirname, "./src/lib"),
    },
  },
  server: {
    port: 5173,
    open: true,
  },
  build: {
    target: "esnext",
    minify: "esbuild",
  },
  assetsInclude: ["**/*.gz"],
});

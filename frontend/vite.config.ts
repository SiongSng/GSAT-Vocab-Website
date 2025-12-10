import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import path from "path";

export default defineConfig({
  plugins: [svelte()],
  base: process.env.GITHUB_ACTIONS ? "/GSAT-Vocab-Website/" : "/",
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
});

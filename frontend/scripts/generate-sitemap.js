#!/usr/bin/env bun

import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const BASE_URL = "https://siongsng.github.io/GSAT-Vocab-Website";
const VOCAB_JSON_PATH = join(__dirname, "../public/data/vocab.json");
const SITEMAP_PATH = join(__dirname, "../public/sitemap.xml");

const STATIC_PAGES = [
  { url: "/", priority: "1.0", changefreq: "daily" },
  { url: "/flashcard", priority: "0.8", changefreq: "weekly" },
  { url: "/quiz", priority: "0.8", changefreq: "weekly" },
];

function escapeXml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function generateSitemap() {
  console.log("Reading vocab data...");
  const vocabData = JSON.parse(readFileSync(VOCAB_JSON_PATH, "utf-8"));
  const entries = vocabData.entries || [];

  console.log(`Found ${entries.length} vocabulary entries`);

  const now = new Date().toISOString().split("T")[0];

  let sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n';
  sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

  for (const page of STATIC_PAGES) {
    sitemap += "  <url>\n";
    sitemap += `    <loc>${BASE_URL}${page.url}</loc>\n`;
    sitemap += `    <lastmod>${now}</lastmod>\n`;
    sitemap += `    <changefreq>${page.changefreq}</changefreq>\n`;
    sitemap += `    <priority>${page.priority}</priority>\n`;
    sitemap += "  </url>\n";
  }

  const topWords = entries
    .filter(
      (entry) => entry.type === "word" && entry.frequency?.ml_score != null,
    )
    .sort((a, b) => {
      const scoreA = a.frequency.ml_score;
      const scoreB = b.frequency.ml_score;
      return scoreB - scoreA;
    })
    .slice(0, 100);

  console.log(`Including top ${topWords.length} words in sitemap`);

  for (const entry of topWords) {
    const lemma = escapeXml(entry.lemma);
    const encodedLemma = encodeURIComponent(entry.lemma);

    sitemap += "  <url>\n";
    sitemap += `    <loc>${BASE_URL}/word/${encodedLemma}</loc>\n`;
    sitemap += `    <lastmod>${now}</lastmod>\n`;
    sitemap += `    <changefreq>monthly</changefreq>\n`;
    sitemap += `    <priority>0.5</priority>\n`;
    sitemap += "  </url>\n";
  }

  sitemap += "</urlset>\n";

  writeFileSync(SITEMAP_PATH, sitemap, "utf-8");
  console.log(`✓ Sitemap generated successfully at ${SITEMAP_PATH}`);
  console.log(`  Total URLs: ${STATIC_PAGES.length + topWords.length}`);
}

try {
  generateSitemap();
} catch (error) {
  console.error("Error generating sitemap:", error);
  process.exit(1);
}

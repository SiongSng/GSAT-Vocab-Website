#!/usr/bin/env bun

import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from "fs";
import { gunzipSync } from "zlib";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const STATIC_DATA_DIR = join(__dirname, "../static/data");
const VOCAB_GZ_PATH = join(STATIC_DATA_DIR, "vocab.json.gz");
const WORDS_DIR = join(STATIC_DATA_DIR, "words");
const INDEX_PATH = join(STATIC_DATA_DIR, "index.json");
const ENTRIES_PATH = join(__dirname, "../src/lib/data/word-entries.json");

interface FrequencyData {
    total_appearances: number;
    tested_count: number;
    year_spread: number;
    importance_score?: number;
    ml_score?: number | null;
}

interface WordEntry {
    lemma: string;
    pos: string[];
    level: number | null;
    in_official_list: boolean;
    frequency?: FrequencyData;
    senses: Array<{
        sense_id: string;
        pos: string | null;
        zh_def: string;
        en_def: string;
    }>;
}

interface PhraseEntry {
    phrase: string;
    frequency?: FrequencyData;
}

interface VocabDatabase {
    version: string;
    generated_at: string;
    metadata: {
        total_entries: number;
        count_by_type: Record<string, number>;
    };
    words: WordEntry[];
    phrases: PhraseEntry[];
    patterns: unknown[];
}

function normalizeImportanceScores(words: WordEntry[], phrases: PhraseEntry[]): void {
    const allScores: number[] = [];

    for (const word of words) {
        if (word.frequency?.ml_score != null) {
            allScores.push(word.frequency.ml_score);
        }
    }
    for (const phrase of phrases) {
        if (phrase.frequency?.ml_score != null) {
            allScores.push(phrase.frequency.ml_score);
        }
    }

    if (allScores.length === 0) {
        for (const word of words) {
            if (word.frequency) {
                word.frequency.importance_score = Math.min(
                    word.frequency.total_appearances / 100,
                    1
                );
            }
        }
        for (const phrase of phrases) {
            if (phrase.frequency) {
                phrase.frequency.importance_score = Math.min(
                    phrase.frequency.total_appearances / 100,
                    1
                );
            }
        }
        return;
    }

    const sortedScores = [...allScores].sort((a, b) => a - b);
    const n = sortedScores.length;

    const scoreToPercentile = new Map<number, number>();
    for (let i = 0; i < n; i++) {
        const score = sortedScores[i];
        if (!scoreToPercentile.has(score)) {
            let j = i;
            while (j < n && sortedScores[j] === score) j++;
            const avgRank = (i + j - 1) / 2;
            scoreToPercentile.set(score, n > 1 ? avgRank / (n - 1) : 0.5);
        }
    }

    for (const word of words) {
        if (word.frequency) {
            word.frequency.importance_score =
                word.frequency.ml_score != null
                    ? (scoreToPercentile.get(word.frequency.ml_score) ?? 0)
                    : Math.min(word.frequency.total_appearances / 100, 1);
        }
    }

    for (const phrase of phrases) {
        if (phrase.frequency) {
            phrase.frequency.importance_score =
                phrase.frequency.ml_score != null
                    ? (scoreToPercentile.get(phrase.frequency.ml_score) ?? 0)
                    : Math.min(phrase.frequency.total_appearances / 100, 1);
        }
    }
}

function safeFilename(lemma: string): string {
    return encodeURIComponent(lemma).replace(/%/g, "_");
}

function generateWordData() {
    console.log("Reading vocab data from static/data/vocab.json.gz...");

    if (!existsSync(VOCAB_GZ_PATH)) {
        console.error(`Error: vocab.json.gz not found at ${VOCAB_GZ_PATH}`);
        console.log("Please ensure vocab.json.gz and version.json are in static/data/");
        process.exit(1);
    }

    const compressed = readFileSync(VOCAB_GZ_PATH);
    const decompressed = gunzipSync(compressed);
    const vocab: VocabDatabase = JSON.parse(decompressed.toString("utf-8"));

    console.log(`Found ${vocab.words.length} words, ${vocab.phrases.length} phrases`);

    console.log("Computing importance scores from ml_score...");
    normalizeImportanceScores(vocab.words, vocab.phrases);

    if (existsSync(WORDS_DIR)) {
        console.log("Cleaning existing words directory...");
        rmSync(WORDS_DIR, { recursive: true });
    }
    mkdirSync(WORDS_DIR, { recursive: true });

    const libDataDir = dirname(ENTRIES_PATH);
    if (!existsSync(libDataDir)) {
        mkdirSync(libDataDir, { recursive: true });
    }

    console.log("Generating individual word JSON files...");
    let count = 0;
    for (const word of vocab.words) {
        const filename = safeFilename(word.lemma) + ".json";
        const filepath = join(WORDS_DIR, filename);
        writeFileSync(filepath, JSON.stringify(word));
        count++;
        if (count % 500 === 0) {
            console.log(`  Processed ${count} words...`);
        }
    }
    console.log(`  Total: ${count} word files created`);

    console.log("Generating index.json for word list...");
    const index = vocab.words.map((w) => ({
        lemma: w.lemma,
        pos: w.pos,
        level: w.level,
        in_official_list: w.in_official_list,
        zh_preview: w.senses?.[0]?.zh_def?.slice(0, 30) || "",
        importance_score: w.frequency?.importance_score || 0,
        tested_count: w.frequency?.tested_count || 0,
        year_spread: w.frequency?.year_spread || 0,
        total_appearances: w.frequency?.total_appearances || 0,
    }));
    writeFileSync(INDEX_PATH, JSON.stringify(index));
    console.log(`  Index created with ${index.length} entries`);

    console.log("Generating word-entries.json for SSG prerender...");
    const entries = vocab.words.map((w) => w.lemma);
    writeFileSync(ENTRIES_PATH, JSON.stringify(entries));
    console.log(`  Entries list created with ${entries.length} items`);

    console.log("\n✓ Word data generation complete!");
    console.log(`  - Source: ${VOCAB_GZ_PATH}`);
    console.log(`  - Individual word files: ${WORDS_DIR}`);
    console.log(`  - Index file: ${INDEX_PATH}`);
    console.log(`  - Entries file: ${ENTRIES_PATH}`);
}

try {
    generateWordData();
} catch (error) {
    console.error("Error generating word data:", error);
    process.exit(1);
}

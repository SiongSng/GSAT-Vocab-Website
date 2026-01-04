import { openDB, type IDBPDatabase, type DBSchema } from "idb";
import type {
  WordEntry,
  PhraseEntry,
  PatternEntry,
  WordIndexItem,
  PhraseIndexItem,
  PatternIndexItem,
  VocabIndexItem,
  VocabMetadata,
  createWordIndexItem,
  createPhraseIndexItem,
  createPatternIndexItem,
} from "$lib/types/vocab";

const DB_NAME = "gsat-vocab-v3";
const DB_VERSION = 1;

interface VocabDBSchema extends DBSchema {
  words: {
    key: string;
    value: WordEntry;
    indexes: {
      by_level: number;
      by_pos: string;
    };
  };
  phrases: {
    key: string;
    value: PhraseEntry;
  };
  patterns: {
    key: string;
    value: PatternEntry;
    indexes: {
      by_category: string;
    };
  };
  metadata: {
    key: string;
    value: { key: string; value: unknown };
  };
}

let db: IDBPDatabase<VocabDBSchema> | null = null;
let indexCache: VocabIndexItem[] | null = null;
let wordsCache: Map<string, WordEntry> = new Map();
let phrasesCache: Map<string, PhraseEntry> = new Map();
let patternsCache: Map<string, PatternEntry> = new Map();

async function getDB(): Promise<IDBPDatabase<VocabDBSchema>> {
  if (db) return db;

  db = await openDB<VocabDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(database) {
      if (!database.objectStoreNames.contains("words")) {
        const wordsStore = database.createObjectStore("words", {
          keyPath: "lemma",
        });
        wordsStore.createIndex("by_level", "level");
        wordsStore.createIndex("by_pos", "pos", { multiEntry: true });
      }

      if (!database.objectStoreNames.contains("phrases")) {
        database.createObjectStore("phrases", { keyPath: "lemma" });
      }

      if (!database.objectStoreNames.contains("patterns")) {
        const patternsStore = database.createObjectStore("patterns", {
          keyPath: "lemma",
        });
        patternsStore.createIndex("by_category", "pattern_category");
      }

      if (!database.objectStoreNames.contains("metadata")) {
        database.createObjectStore("metadata", { keyPath: "key" });
      }
    },
  });

  return db;
}

export async function initVocabDB(): Promise<void> {
  await getDB();
}

export async function getStoredVersion(): Promise<string | null> {
  const database = await getDB();
  const result = await database.get("metadata", "version");
  return result?.value as string | null;
}

export async function setStoredVersion(version: string): Promise<void> {
  const database = await getDB();
  await database.put("metadata", { key: "version", value: version });
}

export async function getStoredMetadata(): Promise<VocabMetadata | null> {
  const database = await getDB();
  const result = await database.get("metadata", "vocab_metadata");
  return result?.value as VocabMetadata | null;
}

export async function setStoredMetadata(
  metadata: VocabMetadata,
): Promise<void> {
  const database = await getDB();
  await database.put("metadata", { key: "vocab_metadata", value: metadata });
}

export async function clearAllStores(): Promise<void> {
  const database = await getDB();
  await database.clear("words");
  await database.clear("phrases");
  await database.clear("patterns");
  wordsCache.clear();
  phrasesCache.clear();
  patternsCache.clear();
  indexCache = null;
}

export async function bulkInsertWords(
  words: WordEntry[],
  onProgress?: (current: number, total: number) => void,
): Promise<void> {
  const database = await getDB();
  const batchSize = 100;
  const total = words.length;

  for (let i = 0; i < total; i += batchSize) {
    const batch = words.slice(i, i + batchSize);
    const tx = database.transaction("words", "readwrite");
    const store = tx.objectStore("words");

    for (const word of batch) {
      store.put(word);
      wordsCache.set(word.lemma, word);
    }

    await tx.done;
    onProgress?.(Math.min(i + batchSize, total), total);
  }

  indexCache = null;
}

export async function bulkInsertPhrases(phrases: PhraseEntry[]): Promise<void> {
  const database = await getDB();
  const tx = database.transaction("phrases", "readwrite");
  const store = tx.objectStore("phrases");

  for (const phrase of phrases) {
    store.put(phrase);
    phrasesCache.set(phrase.lemma, phrase);
  }

  await tx.done;
  indexCache = null;
}

export async function bulkInsertPatterns(
  patterns: PatternEntry[],
): Promise<void> {
  const database = await getDB();
  const tx = database.transaction("patterns", "readwrite");
  const store = tx.objectStore("patterns");

  for (const pattern of patterns) {
    store.put(pattern);
    patternsCache.set(pattern.lemma, pattern);
  }

  await tx.done;
  indexCache = null;
}

export function getWordCached(lemma: string): WordEntry | undefined {
  return wordsCache.get(lemma);
}

export function getPhraseCached(lemma: string): PhraseEntry | undefined {
  return phrasesCache.get(lemma);
}

export function getPatternCached(lemma: string): PatternEntry | undefined {
  return patternsCache.get(lemma);
}

export async function getWord(lemma: string): Promise<WordEntry | undefined> {
  const cached = wordsCache.get(lemma);
  if (cached) return cached;

  const database = await getDB();
  const entry = await database.get("words", lemma);
  if (entry) {
    wordsCache.set(lemma, entry);
  }
  return entry;
}

export async function getPhrase(
  lemma: string,
): Promise<PhraseEntry | undefined> {
  const cached = phrasesCache.get(lemma);
  if (cached) return cached;

  const database = await getDB();
  const entry = await database.get("phrases", lemma);
  if (entry) {
    phrasesCache.set(lemma, entry);
  }
  return entry;
}

export async function getPattern(
  lemma: string,
): Promise<PatternEntry | undefined> {
  const cached = patternsCache.get(lemma);
  if (cached) return cached;

  const database = await getDB();
  const entry = await database.get("patterns", lemma);
  if (entry) {
    patternsCache.set(lemma, entry);
  }
  return entry;
}

export async function getAllWords(): Promise<WordEntry[]> {
  const database = await getDB();
  return database.getAll("words");
}

export async function getAllPhrases(): Promise<PhraseEntry[]> {
  const database = await getDB();
  return database.getAll("phrases");
}

export async function getAllPatterns(): Promise<PatternEntry[]> {
  const database = await getDB();
  return database.getAll("patterns");
}

export async function getWordsCount(): Promise<number> {
  const database = await getDB();
  return database.count("words");
}

export async function getPhrasesCount(): Promise<number> {
  const database = await getDB();
  return database.count("phrases");
}

export async function getPatternsCount(): Promise<number> {
  const database = await getDB();
  return database.count("patterns");
}

export async function getTotalEntriesCount(): Promise<number> {
  const [words, phrases, patterns] = await Promise.all([
    getWordsCount(),
    getPhrasesCount(),
    getPatternsCount(),
  ]);
  return words + phrases + patterns;
}

export async function buildIndex(
  createWordIndexFn: typeof createWordIndexItem,
  createPhraseIndexFn: typeof createPhraseIndexItem,
  createPatternIndexFn: typeof createPatternIndexItem,
): Promise<VocabIndexItem[]> {
  if (indexCache) {
    return indexCache;
  }

  const [words, phrases, patterns] = await Promise.all([
    getAllWords(),
    getAllPhrases(),
    getAllPatterns(),
  ]);

  const wordItems: WordIndexItem[] = words.map(createWordIndexFn);
  const phraseItems: PhraseIndexItem[] = phrases.map(createPhraseIndexFn);
  const patternItems: PatternIndexItem[] = patterns.map(createPatternIndexFn);

  const index: VocabIndexItem[] = [
    ...wordItems,
    ...phraseItems,
    ...patternItems,
  ];

  index.sort((a, b) => {
    if (a.type === "pattern" && b.type !== "pattern") return 1;
    if (a.type !== "pattern" && b.type === "pattern") return -1;

    const aScore = "importance_score" in a ? a.importance_score : 0;
    const bScore = "importance_score" in b ? b.importance_score : 0;
    return bScore - aScore;
  });

  indexCache = index;
  return index;
}

export async function getWordsByLevel(level: number): Promise<WordEntry[]> {
  const database = await getDB();
  return database.getAllFromIndex("words", "by_level", level);
}

export async function getPatternsByCategory(
  category: string,
): Promise<PatternEntry[]> {
  const database = await getDB();
  return database.getAllFromIndex("patterns", "by_category", category);
}

export function clearIndexCache(): void {
  indexCache = null;
}

export async function closeDB(): Promise<void> {
  if (db) {
    db.close();
    db = null;
  }
  wordsCache.clear();
  phrasesCache.clear();
  patternsCache.clear();
  indexCache = null;
}

export async function getSRSEligibleEntry(
  lemma: string,
): Promise<WordEntry | PhraseEntry | undefined> {
  const word = await getWord(lemma);
  if (word) return word;
  return getPhrase(lemma);
}

export function getSRSEligibleEntryCached(
  lemma: string,
): WordEntry | PhraseEntry | undefined {
  const word = getWordCached(lemma);
  if (word) return word;
  return getPhraseCached(lemma);
}

export async function lookupEntry(
  lemma: string,
  type?: "word" | "phrase" | "pattern",
): Promise<WordEntry | PhraseEntry | PatternEntry | undefined> {
  if (type === "word") return getWord(lemma);
  if (type === "phrase") return getPhrase(lemma);
  if (type === "pattern") return getPattern(lemma);

  const word = await getWord(lemma);
  if (word) return word;
  const phrase = await getPhrase(lemma);
  if (phrase) return phrase;
  return getPattern(lemma);
}

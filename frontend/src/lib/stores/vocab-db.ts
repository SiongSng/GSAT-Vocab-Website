import { openDB, type IDBPDatabase, type DBSchema } from "idb";
import type {
  VocabEntry,
  VocabIndexItem,
  DistractorGroup,
  VocabMetadata,
  createIndexItem,
} from "$lib/types/vocab";

const DB_NAME = "gsat-vocab-v2";
const DB_VERSION = 2;

interface VocabDBSchema extends DBSchema {
  entries: {
    key: string;
    value: VocabEntry;
    indexes: {
      by_level: number;
      by_tier: string;
      by_type: string;
    };
  };
  distractor_groups: {
    key: number;
    value: DistractorGroup & { id: number };
    indexes: {
      by_correct_answer: string;
      by_year: number;
    };
  };
  metadata: {
    key: string;
    value: { key: string; value: unknown };
  };
}

let db: IDBPDatabase<VocabDBSchema> | null = null;
let indexCache: VocabIndexItem[] | null = null;
let entriesCache: Map<string, VocabEntry> = new Map();
let distractorGroupsCache: DistractorGroup[] | null = null;

async function getDB(): Promise<IDBPDatabase<VocabDBSchema>> {
  if (db) return db;

  db = await openDB<VocabDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(database, oldVersion) {
      if (oldVersion < 1) {
        const entriesStore = database.createObjectStore("entries", {
          keyPath: "lemma",
        });
        entriesStore.createIndex("by_level", "level");
        entriesStore.createIndex("by_tier", "tier");
        entriesStore.createIndex("by_type", "type");

        database.createObjectStore("metadata", { keyPath: "key" });
      }

      if (oldVersion < 2) {
        if (!database.objectStoreNames.contains("distractor_groups")) {
          const distractorStore = database.createObjectStore(
            "distractor_groups",
            { keyPath: "id", autoIncrement: true }
          );
          distractorStore.createIndex("by_correct_answer", "correct_answer");
          distractorStore.createIndex("by_year", "source.year");
        }
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

export async function setStoredMetadata(metadata: VocabMetadata): Promise<void> {
  const database = await getDB();
  await database.put("metadata", { key: "vocab_metadata", value: metadata });
}

export async function clearAllStores(): Promise<void> {
  const database = await getDB();
  await database.clear("entries");
  await database.clear("distractor_groups");
  entriesCache.clear();
  indexCache = null;
  distractorGroupsCache = null;
}

export async function bulkInsertEntries(
  entries: VocabEntry[],
  onProgress?: (current: number, total: number) => void
): Promise<void> {
  const database = await getDB();
  const batchSize = 100;
  const total = entries.length;

  for (let i = 0; i < total; i += batchSize) {
    const batch = entries.slice(i, i + batchSize);
    const tx = database.transaction("entries", "readwrite");
    const store = tx.objectStore("entries");

    for (const entry of batch) {
      store.put(entry);
      entriesCache.set(entry.lemma, entry);
    }

    await tx.done;
    onProgress?.(Math.min(i + batchSize, total), total);
  }

  indexCache = null;
}

export async function bulkInsertDistractorGroups(
  groups: DistractorGroup[]
): Promise<void> {
  const database = await getDB();
  const tx = database.transaction("distractor_groups", "readwrite");
  const store = tx.objectStore("distractor_groups");

  for (const group of groups) {
    store.add(group as DistractorGroup & { id: number });
  }

  await tx.done;
  distractorGroupsCache = null;
}

export async function getEntry(lemma: string): Promise<VocabEntry | undefined> {
  if (entriesCache.has(lemma)) {
    return entriesCache.get(lemma);
  }

  const database = await getDB();
  const entry = await database.get("entries", lemma);
  if (entry) {
    entriesCache.set(lemma, entry);
  }
  return entry;
}

export async function getAllEntries(): Promise<VocabEntry[]> {
  const database = await getDB();
  return database.getAll("entries");
}

export async function getEntriesCount(): Promise<number> {
  const database = await getDB();
  return database.count("entries");
}

export async function buildIndex(
  createIndexItemFn: typeof createIndexItem
): Promise<VocabIndexItem[]> {
  if (indexCache) {
    return indexCache;
  }

  const entries = await getAllEntries();
  const index = entries.map(createIndexItemFn);

  index.sort((a, b) => b.importance_score - a.importance_score);

  indexCache = index;
  return index;
}

export async function getEntriesByLevel(level: number): Promise<VocabEntry[]> {
  const database = await getDB();
  return database.getAllFromIndex("entries", "by_level", level);
}

export async function getEntriesByTier(tier: string): Promise<VocabEntry[]> {
  const database = await getDB();
  return database.getAllFromIndex("entries", "by_tier", tier);
}

export async function getEntriesByType(type: string): Promise<VocabEntry[]> {
  const database = await getDB();
  return database.getAllFromIndex("entries", "by_type", type);
}

export async function getAllDistractorGroups(): Promise<DistractorGroup[]> {
  if (distractorGroupsCache) {
    return distractorGroupsCache;
  }

  const database = await getDB();
  const groups = await database.getAll("distractor_groups");
  distractorGroupsCache = groups;
  return groups;
}

export async function getDistractorGroupsByWord(
  lemma: string
): Promise<DistractorGroup[]> {
  const database = await getDB();
  const asCorrect = await database.getAllFromIndex(
    "distractor_groups",
    "by_correct_answer",
    lemma
  );

  const allGroups = await getAllDistractorGroups();
  const asDistractor = allGroups.filter((g) => g.distractors.includes(lemma));

  const seen = new Set<string>();
  const result: DistractorGroup[] = [];

  for (const g of [...asCorrect, ...asDistractor]) {
    const key = `${g.correct_answer}-${g.question_context}`;
    if (!seen.has(key)) {
      seen.add(key);
      result.push(g);
    }
  }

  return result;
}

export async function getConfusedWords(lemma: string): Promise<string[]> {
  const groups = await getDistractorGroupsByWord(lemma);
  const confused = new Set<string>();

  for (const group of groups) {
    if (group.correct_answer === lemma) {
      group.distractors.forEach((d) => confused.add(d));
    } else {
      confused.add(group.correct_answer);
      group.distractors
        .filter((d) => d !== lemma)
        .forEach((d) => confused.add(d));
    }
  }

  return Array.from(confused);
}

export function clearIndexCache(): void {
  indexCache = null;
}

export function clearDistractorGroupsCache(): void {
  distractorGroupsCache = null;
}

export async function closeDB(): Promise<void> {
  if (db) {
    db.close();
    db = null;
  }
  entriesCache.clear();
  indexCache = null;
  distractorGroupsCache = null;
}

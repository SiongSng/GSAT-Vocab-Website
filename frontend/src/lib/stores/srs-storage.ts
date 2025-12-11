import { openDB, type IDBPDatabase } from "idb";
import type { SRSCard, SRSReviewLog } from "$lib/types/srs";
import { createEmptyCard, State } from "ts-fsrs";

const DB_NAME = "gsat-vocab-srs";
const DB_VERSION = 1;
const CARDS_STORE = "cards";
const LOGS_STORE = "logs";
const META_STORE = "meta";

interface SRSDatabase {
  cards: SRSCard;
  logs: SRSReviewLog;
  meta: { key: string; value: unknown };
}

let db: IDBPDatabase<SRSDatabase> | null = null;
let cardsCache: Map<string, SRSCard> = new Map();
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const SAVE_DEBOUNCE_MS = 1000;

async function getDB(): Promise<IDBPDatabase<SRSDatabase>> {
  if (db) return db;

  db = await openDB<SRSDatabase>(DB_NAME, DB_VERSION, {
    upgrade(database) {
      if (!database.objectStoreNames.contains(CARDS_STORE)) {
        const cardsStore = database.createObjectStore(CARDS_STORE, {
          keyPath: "lemma",
        });
        cardsStore.createIndex("due", "due");
        cardsStore.createIndex("state", "state");
      }

      if (!database.objectStoreNames.contains(LOGS_STORE)) {
        const logsStore = database.createObjectStore(LOGS_STORE, {
          keyPath: ["lemma", "review"],
        });
        logsStore.createIndex("lemma", "lemma");
        logsStore.createIndex("review", "review");
      }

      if (!database.objectStoreNames.contains(META_STORE)) {
        database.createObjectStore(META_STORE, { keyPath: "key" });
      }
    },
  });

  return db;
}

export async function initStorage(): Promise<void> {
  const database = await getDB();
  const cards = await database.getAll(CARDS_STORE);
  cardsCache = new Map(cards.map((card) => [card.lemma, card]));
}

export function getCard(lemma: string): SRSCard | undefined {
  return cardsCache.get(lemma);
}

export function getAllCards(): SRSCard[] {
  return Array.from(cardsCache.values());
}

export function getCardsByState(state: State): SRSCard[] {
  return getAllCards().filter((card) => card.state === state);
}

export function getDueCards(now: Date = new Date()): SRSCard[] {
  return getAllCards().filter((card) => new Date(card.due) <= now);
}

export function getNewCards(): SRSCard[] {
  return getCardsByState(State.New);
}

export function getLearningCards(): SRSCard[] {
  return getAllCards().filter(
    (card) => card.state === State.Learning || card.state === State.Relearning
  );
}

export function getReviewCards(now: Date = new Date()): SRSCard[] {
  return getAllCards().filter(
    (card) => card.state === State.Review && new Date(card.due) <= now
  );
}

export function createCard(lemma: string): SRSCard {
  const baseCard = createEmptyCard();
  const card: SRSCard = {
    ...baseCard,
    lemma,
  };
  return card;
}

export function ensureCard(lemma: string): SRSCard {
  let card = getCard(lemma);
  if (!card) {
    card = createCard(lemma);
    cardsCache.set(lemma, card);
    scheduleSave();
  }
  return card;
}

export function updateCard(card: SRSCard): void {
  cardsCache.set(card.lemma, card);
  scheduleSave();
}

export async function addReviewLog(log: SRSReviewLog): Promise<void> {
  const database = await getDB();
  await database.add(LOGS_STORE, log);
}

export async function getReviewLogs(lemma: string): Promise<SRSReviewLog[]> {
  const database = await getDB();
  return database.getAllFromIndex(LOGS_STORE, "lemma", lemma);
}

export async function getAllReviewLogs(): Promise<SRSReviewLog[]> {
  const database = await getDB();
  return database.getAll(LOGS_STORE);
}

function scheduleSave(): void {
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
  }
  saveDebounceTimer = setTimeout(() => {
    flushToIndexedDB();
    saveDebounceTimer = null;
  }, SAVE_DEBOUNCE_MS);
}

async function flushToIndexedDB(): Promise<void> {
  const database = await getDB();
  const tx = database.transaction(CARDS_STORE, "readwrite");
  const store = tx.objectStore(CARDS_STORE);

  const promises: Promise<IDBValidKey>[] = Array.from(cardsCache.values()).map(
    (card) => store.put(card)
  );
  await Promise.all(promises);
  await tx.done;
}

export async function forceSave(): Promise<void> {
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
    saveDebounceTimer = null;
  }
  await flushToIndexedDB();
}

export async function getMeta<T>(key: string): Promise<T | undefined> {
  const database = await getDB();
  const result = await database.get(META_STORE, key);
  return result?.value as T | undefined;
}

export async function setMeta<T>(key: string, value: T): Promise<void> {
  const database = await getDB();
  await database.put(META_STORE, { key, value });
}

export async function clearAllData(): Promise<void> {
  const database = await getDB();
  await database.clear(CARDS_STORE);
  await database.clear(LOGS_STORE);
  await database.clear(META_STORE);
  cardsCache.clear();
}

export function getCacheSize(): number {
  return cardsCache.size;
}

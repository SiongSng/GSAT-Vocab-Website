import { openDB, type IDBPDatabase, deleteDB } from "idb";
import type { SRSCard, SRSReviewLog } from "$lib/types/srs";
import { createCardKey } from "$lib/types/srs";
import { createEmptyCard, State } from "ts-fsrs";

const DB_NAME = "gsat-vocab-srs-v2";
const DB_VERSION = 1;
const CARDS_STORE = "cards";
const LOGS_STORE = "logs";
const META_STORE = "meta";

const OLD_DB_NAME = "gsat-vocab-srs";

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
          keyPath: ["lemma", "sense_id"],
        });
        cardsStore.createIndex("due", "due");
        cardsStore.createIndex("state", "state");
        cardsStore.createIndex("lemma", "lemma");
      }

      if (!database.objectStoreNames.contains(LOGS_STORE)) {
        const logsStore = database.createObjectStore(LOGS_STORE, {
          keyPath: ["lemma", "sense_id", "review"],
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

async function migrateFromOldDB(): Promise<boolean> {
  try {
    const databases = await indexedDB.databases();
    const oldExists = databases.some(d => d.name === OLD_DB_NAME);
    if (!oldExists) return false;

    const oldDB = await openDB(OLD_DB_NAME, 1);
    const oldCards = await oldDB.getAll("cards");
    oldDB.close();

    if (oldCards.length === 0) {
      await deleteDB(OLD_DB_NAME);
      return false;
    }

    const database = await getDB();
    const tx = database.transaction(CARDS_STORE, "readwrite");
    const store = tx.objectStore(CARDS_STORE);

    for (const oldCard of oldCards) {
      const migratedCard: SRSCard = {
        ...oldCard,
        sense_id: "primary",
      };
      await store.put(migratedCard);
    }

    await tx.done;
    await deleteDB(OLD_DB_NAME);

    return true;
  } catch {
    return false;
  }
}

export async function initStorage(): Promise<void> {
  const database = await getDB();

  const migrated = await migrateFromOldDB();
  if (migrated) {
    const cards = await database.getAll(CARDS_STORE);
    cardsCache = new Map(cards.map((card) => [createCardKey(card.lemma, card.sense_id), card]));
  } else {
    const cards = await database.getAll(CARDS_STORE);
    cardsCache = new Map(cards.map((card) => [createCardKey(card.lemma, card.sense_id), card]));
  }
}

export function getCard(lemma: string, senseId: string): SRSCard | undefined {
  return cardsCache.get(createCardKey(lemma, senseId));
}

export function getCardsByLemma(lemma: string): SRSCard[] {
  const cards: SRSCard[] = [];
  for (const card of cardsCache.values()) {
    if (card.lemma === lemma) {
      cards.push(card);
    }
  }
  return cards;
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

export function createCard(lemma: string, senseId: string): SRSCard {
  const baseCard = createEmptyCard();
  const card: SRSCard = {
    ...baseCard,
    lemma,
    sense_id: senseId,
  };
  return card;
}

export function ensureCard(lemma: string, senseId: string): SRSCard {
  const key = createCardKey(lemma, senseId);
  let card = cardsCache.get(key);
  if (!card) {
    card = createCard(lemma, senseId);
    cardsCache.set(key, card);
    scheduleSave();
  }
  return card;
}

export function updateCard(card: SRSCard): void {
  cardsCache.set(createCardKey(card.lemma, card.sense_id), card);
  scheduleSave();
}

export async function addReviewLog(log: SRSReviewLog): Promise<void> {
  const database = await getDB();
  await database.add(LOGS_STORE, log);
}

export async function getReviewLogs(lemma: string, senseId?: string): Promise<SRSReviewLog[]> {
  const database = await getDB();
  const allLogs = await database.getAllFromIndex(LOGS_STORE, "lemma", lemma);
  if (senseId) {
    return allLogs.filter(log => log.sense_id === senseId);
  }
  return allLogs;
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

export function hasCardForLemma(lemma: string): boolean {
  for (const card of cardsCache.values()) {
    if (card.lemma === lemma) {
      return true;
    }
  }
  return false;
}

export function getPrimaryCard(lemma: string): SRSCard | undefined {
  const cards = getCardsByLemma(lemma);
  return cards.find(c => c.sense_id === "primary") || cards[0];
}

export function getStableSenseCards(lemma: string, stabilityThreshold: number = 10): SRSCard[] {
  return getCardsByLemma(lemma).filter(card => card.stability >= stabilityThreshold);
}

export function shouldUnlockSecondarySenses(lemma: string): boolean {
  const primaryCard = getCard(lemma, "primary");
  if (!primaryCard) return false;
  return primaryCard.stability >= 10 && primaryCard.state === State.Review;
}

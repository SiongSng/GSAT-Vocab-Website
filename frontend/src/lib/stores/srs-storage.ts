import { openDB, type IDBPDatabase, deleteDB } from "idb";
import type {
  SRSCard,
  SRSReviewLog,
  DailyStats,
  SessionLog,
} from "$lib/types/srs";
import { createCardKey } from "$lib/types/srs";
import { createEmptyCard, State, Rating } from "ts-fsrs";

const DB_NAME = "gsat-vocab-srs-v2";
const DB_VERSION = 2;
const CARDS_STORE = "cards";
const LOGS_STORE = "logs";
const META_STORE = "meta";
const DAILY_STATS_STORE = "daily_stats";
const SESSION_LOGS_STORE = "session_logs";

const OLD_DB_NAME = "gsat-vocab-srs";

interface SRSDatabase {
  cards: SRSCard;
  logs: SRSReviewLog;
  meta: { key: string; value: unknown };
  daily_stats: DailyStats;
  session_logs: SessionLog;
}

let db: IDBPDatabase<SRSDatabase> | null = null;
let cardsCache: Map<string, SRSCard> = new Map();
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const SAVE_DEBOUNCE_MS = 1000;

type DataChangeCallback = () => void;
const dataChangeCallbacks: Set<DataChangeCallback> = new Set();

export function onDataChange(callback: DataChangeCallback): () => void {
  dataChangeCallbacks.add(callback);
  return () => dataChangeCallbacks.delete(callback);
}

function notifyDataChange(): void {
  for (const callback of dataChangeCallbacks) {
    callback();
  }
}

async function getDB(): Promise<IDBPDatabase<SRSDatabase>> {
  if (db) return db;

  db = await openDB<SRSDatabase>(DB_NAME, DB_VERSION, {
    upgrade(database, oldVersion) {
      if (oldVersion < 1) {
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
      }

      if (oldVersion < 2) {
        if (!database.objectStoreNames.contains(DAILY_STATS_STORE)) {
          database.createObjectStore(DAILY_STATS_STORE, { keyPath: "date" });
        }

        if (!database.objectStoreNames.contains(SESSION_LOGS_STORE)) {
          const sessionStore = database.createObjectStore(SESSION_LOGS_STORE, {
            keyPath: "id",
            autoIncrement: true,
          });
          sessionStore.createIndex("session_id", "session_id");
          sessionStore.createIndex("start", "start");
        }
      }
    },
  });

  return db;
}

async function migrateFromOldDB(): Promise<boolean> {
  try {
    const databases = await indexedDB.databases();
    const oldExists = databases.some((d) => d.name === OLD_DB_NAME);
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
    cardsCache = new Map(
      cards.map((card) => [createCardKey(card.lemma, card.sense_id), card]),
    );
  } else {
    const cards = await database.getAll(CARDS_STORE);
    cardsCache = new Map(
      cards.map((card) => [createCardKey(card.lemma, card.sense_id), card]),
    );
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
    (card) => card.state === State.Learning || card.state === State.Relearning,
  );
}

export function getReviewCards(now: Date = new Date()): SRSCard[] {
  return getAllCards().filter(
    (card) => card.state === State.Review && new Date(card.due) <= now,
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
  setLastUpdated(Date.now());
  scheduleSave();
}

export async function setAllCards(cards: SRSCard[]): Promise<void> {
  const database = await getDB();
  const tx = database.transaction(CARDS_STORE, "readwrite");
  const store = tx.objectStore(CARDS_STORE);
  await store.clear();
  cardsCache.clear();
  for (const card of cards) {
    cardsCache.set(createCardKey(card.lemma, card.sense_id), card);
    await store.put(card);
  }
  await tx.done;
}

export async function getLastUpdated(): Promise<number> {
  const val = await getMeta("last_updated");
  return typeof val === "number" ? val : 0;
}

export async function setLastUpdated(ts: number): Promise<void> {
  await setMeta("last_updated", ts);
}

export async function addReviewLog(log: SRSReviewLog): Promise<void> {
  const database = await getDB();
  await database.add(LOGS_STORE, log);
}

export async function getReviewLogs(
  lemma: string,
  senseId?: string,
): Promise<SRSReviewLog[]> {
  const database = await getDB();
  const allLogs = await database.getAllFromIndex(LOGS_STORE, "lemma", lemma);
  if (senseId) {
    return allLogs.filter((log) => log.sense_id === senseId);
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
    (card) => store.put(card),
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
  return cards.find((c) => c.sense_id === "primary") || cards[0];
}

export function getStableSenseCards(
  lemma: string,
  stabilityThreshold: number = 10,
): SRSCard[] {
  return getCardsByLemma(lemma).filter(
    (card) => card.stability >= stabilityThreshold,
  );
}

export function shouldUnlockSecondarySenses(lemma: string): boolean {
  const primaryCard = getCard(lemma, "primary");
  if (!primaryCard) return false;
  return primaryCard.stability >= 10 && primaryCard.state === State.Review;
}

function getTodayDateKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function createEmptyDailyStats(date: string): DailyStats {
  return {
    date,
    new_cards: 0,
    reviews: 0,
    again: 0,
    hard: 0,
    good: 0,
    easy: 0,
    study_time_ms: 0,
    updated_at: Date.now(),
  };
}

export async function getDailyStats(
  rangeStart?: string,
  rangeEnd?: string,
): Promise<DailyStats[]> {
  const database = await getDB();
  const all = await database.getAll(DAILY_STATS_STORE);

  if (!rangeStart && !rangeEnd) return all;

  return all.filter((stat) => {
    if (rangeStart && stat.date < rangeStart) return false;
    if (rangeEnd && stat.date > rangeEnd) return false;
    return true;
  });
}

export async function getAllDailyStats(): Promise<DailyStats[]> {
  const database = await getDB();
  return database.getAll(DAILY_STATS_STORE);
}

export async function setAllDailyStats(stats: DailyStats[]): Promise<void> {
  const database = await getDB();
  const tx = database.transaction(DAILY_STATS_STORE, "readwrite");
  const store = tx.objectStore(DAILY_STATS_STORE);
  await store.clear();
  for (const stat of stats) {
    await store.put(stat);
  }
  await tx.done;
}

export async function getTodayStats(): Promise<DailyStats> {
  const today = getTodayDateKey();
  const database = await getDB();
  const stats = await database.get(DAILY_STATS_STORE, today);
  return stats || createEmptyDailyStats(today);
}

export async function updateDailyStats(
  rating: Rating,
  wasNew: boolean,
  studyTimeMs: number = 0,
): Promise<void> {
  const today = getTodayDateKey();
  const database = await getDB();
  let stats = await database.get(DAILY_STATS_STORE, today);

  if (!stats) {
    stats = createEmptyDailyStats(today);
  }

  if (wasNew) {
    stats.new_cards++;
  } else {
    stats.reviews++;
  }

  switch (rating) {
    case Rating.Again:
      stats.again++;
      break;
    case Rating.Hard:
      stats.hard++;
      break;
    case Rating.Good:
      stats.good++;
      break;
    case Rating.Easy:
      stats.easy++;
      break;
  }

  stats.study_time_ms += studyTimeMs;
  stats.updated_at = Date.now();

  await database.put(DAILY_STATS_STORE, stats);
}

export async function getReviewLogsFiltered(options: {
  lemma?: string;
  sense_id?: string;
  rangeStart?: Date;
  rangeEnd?: Date;
}): Promise<SRSReviewLog[]> {
  const database = await getDB();
  let logs: SRSReviewLog[];

  if (options.lemma) {
    logs = await database.getAllFromIndex(LOGS_STORE, "lemma", options.lemma);
    if (options.sense_id) {
      logs = logs.filter((log) => log.sense_id === options.sense_id);
    }
  } else {
    logs = await database.getAll(LOGS_STORE);
  }

  if (options.rangeStart || options.rangeEnd) {
    logs = logs.filter((log) => {
      const reviewTime = new Date(log.review).getTime();
      if (options.rangeStart && reviewTime < options.rangeStart.getTime())
        return false;
      if (options.rangeEnd && reviewTime > options.rangeEnd.getTime())
        return false;
      return true;
    });
  }

  return logs;
}

export async function addSessionLog(
  sessionId: string,
  start: number,
  end: number,
  studied: number,
): Promise<void> {
  const database = await getDB();
  await database.add(SESSION_LOGS_STORE, {
    session_id: sessionId,
    start,
    end,
    studied,
  });
}

export async function getSessions(
  rangeStart?: Date,
  rangeEnd?: Date,
): Promise<SessionLog[]> {
  const database = await getDB();
  const all = await database.getAll(SESSION_LOGS_STORE);

  if (!rangeStart && !rangeEnd) return all;

  return all.filter((session) => {
    if (rangeStart && session.start < rangeStart.getTime()) return false;
    if (rangeEnd && session.end > rangeEnd.getTime()) return false;
    return true;
  });
}

export interface DatabaseSnapshot {
  cards: SRSCard[];
  logs: SRSReviewLog[];
  stats: DailyStats[];
  sessions: SessionLog[];
  meta: { key: string; value: unknown }[];
}

export async function exportDatabase(): Promise<DatabaseSnapshot> {
  const database = await getDB();
  return {
    cards: await database.getAll(CARDS_STORE),
    logs: await database.getAll(LOGS_STORE),
    stats: await database.getAll(DAILY_STATS_STORE),
    sessions: await database.getAll(SESSION_LOGS_STORE),
    meta: await database.getAll(META_STORE),
  };
}

export async function importDatabase(
  snapshot: DatabaseSnapshot,
): Promise<void> {
  const database = await getDB();

  const tx = database.transaction(
    [
      CARDS_STORE,
      LOGS_STORE,
      DAILY_STATS_STORE,
      SESSION_LOGS_STORE,
      META_STORE,
    ],
    "readwrite",
  );

  await tx.objectStore(CARDS_STORE).clear();
  await tx.objectStore(LOGS_STORE).clear();
  await tx.objectStore(DAILY_STATS_STORE).clear();
  await tx.objectStore(SESSION_LOGS_STORE).clear();
  await tx.objectStore(META_STORE).clear();

  for (const card of snapshot.cards) {
    await tx.objectStore(CARDS_STORE).put(card);
  }
  for (const log of snapshot.logs) {
    await tx.objectStore(LOGS_STORE).put(log);
  }
  for (const stat of snapshot.stats) {
    await tx.objectStore(DAILY_STATS_STORE).put(stat);
  }
  for (const session of snapshot.sessions) {
    await tx.objectStore(SESSION_LOGS_STORE).put(session);
  }
  for (const meta of snapshot.meta) {
    await tx.objectStore(META_STORE).put(meta);
  }

  await tx.done;

  cardsCache.clear();
  for (const card of snapshot.cards) {
    cardsCache.set(createCardKey(card.lemma, card.sense_id), card);
  }

  notifyDataChange();
}

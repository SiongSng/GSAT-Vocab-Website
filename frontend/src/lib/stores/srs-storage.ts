import { openDB, type IDBPDatabase, deleteDB } from "idb";
import type {
  SRSCard,
  SRSReviewLog,
  DailyStats,
  SessionLog,
  SRSEligibleEntry,
  SkillType,
  SkillState,
} from "$lib/types/srs";
import { createCardKey, getPrimarySenseId, getUnlockedSkills } from "$lib/types/srs";
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
let cardsByLemmaCache: Map<string, SRSCard[]> = new Map();
let saveDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let dirtyCardKeys: Set<string> = new Set();
let saveChain: Promise<void> = Promise.resolve();

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
        entry_type: "word" as const,
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

function ensureCardHasEntryType(card: SRSCard): SRSCard {
  if (!card.entry_type) {
    return { ...card, entry_type: "word" as const };
  }
  return card;
}

function rebuildLemmaIndex(cards: SRSCard[]): void {
  cardsByLemmaCache.clear();
  for (const card of cards) {
    const existing = cardsByLemmaCache.get(card.lemma);
    if (existing) {
      existing.push(card);
    } else {
      cardsByLemmaCache.set(card.lemma, [card]);
    }
  }
}

function addToLemmaIndex(card: SRSCard): void {
  const existing = cardsByLemmaCache.get(card.lemma);
  if (existing) {
    const idx = existing.findIndex(
      (c) => c.sense_id === card.sense_id,
    );
    if (idx >= 0) {
      existing[idx] = card;
    } else {
      existing.push(card);
    }
  } else {
    cardsByLemmaCache.set(card.lemma, [card]);
  }
}

function toDate(value: unknown, fallback: Date = new Date()): Date {
  try {
    if (value instanceof Date) {
      return new Date(value.getTime());
    }
    return new Date(value as any);
  } catch {
    return new Date(fallback.getTime());
  }
}

function toNumber(value: unknown, fallback: number = 0): number {
  try {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  } catch {
    return fallback;
  }
}

function toState(value: unknown, fallback: State = State.New): State {
  const n = toNumber(value, fallback);
  return n === State.New || n === State.Learning || n === State.Review || n === State.Relearning
    ? (n as State)
    : fallback;
}

function normalizeSkillStateForStorage(state: SkillState): SkillState {
  return {
    due: toDate(state.due),
    stability: toNumber(state.stability),
    difficulty: toNumber(state.difficulty),
    reps: toNumber(state.reps),
    lapses: toNumber(state.lapses),
    state: toState(state.state),
    last_review: state.last_review ? toDate(state.last_review) : undefined,
  };
}

function normalizeCardForStorage(card: SRSCard): SRSCard {
  const normalizedSkills: SRSCard["skills"] = card.skills
    ? Object.fromEntries(
        Object.entries(card.skills)
          .filter(([, value]) => !!value)
          .map(([skill, value]) => [skill, normalizeSkillStateForStorage(value as SkillState)]),
      )
    : undefined;

  return {
    due: toDate(card.due),
    stability: toNumber(card.stability),
    difficulty: toNumber(card.difficulty),
    elapsed_days: toNumber((card as any).elapsed_days),
    scheduled_days: toNumber((card as any).scheduled_days),
    learning_steps: toNumber((card as any).learning_steps),
    reps: toNumber(card.reps),
    lapses: toNumber(card.lapses),
    state: toState(card.state),
    last_review: card.last_review ? toDate(card.last_review) : undefined,
    lemma: String(card.lemma ?? ""),
    sense_id: String(card.sense_id ?? ""),
    entry_type: card.entry_type === "phrase" ? "phrase" : "word",
    skills: normalizedSkills,
  };
}

function removeFromLemmaIndex(lemma: string, senseId: string): void {
  const existing = cardsByLemmaCache.get(lemma);
  if (existing) {
    const idx = existing.findIndex((c) => c.sense_id === senseId);
    if (idx >= 0) {
      existing.splice(idx, 1);
      if (existing.length === 0) {
        cardsByLemmaCache.delete(lemma);
      }
    }
  }
}

export async function initStorage(): Promise<void> {
  const database = await getDB();

  const migrated = await migrateFromOldDB();
  const cards = await database.getAll(CARDS_STORE);

  let needsUpdate = false;
  const updatedCards: SRSCard[] = [];

  for (const card of cards) {
    const updated = ensureCardHasEntryType(card);
    if (updated !== card) {
      needsUpdate = true;
    }
    updatedCards.push(normalizeCardForStorage(updated));
  }

  if (needsUpdate && !migrated) {
    const tx = database.transaction(CARDS_STORE, "readwrite");
    const store = tx.objectStore(CARDS_STORE);
    for (const card of updatedCards) {
      await store.put(card);
    }
    await tx.done;
  }

  cardsCache = new Map(
    updatedCards.map((card) => [createCardKey(card.lemma, card.sense_id), card]),
  );
  rebuildLemmaIndex(updatedCards);
}

export function getCard(lemma: string, senseId: string): SRSCard | undefined {
  return cardsCache.get(createCardKey(lemma, senseId));
}

export function getCardsByLemma(lemma: string): SRSCard[] {
  return cardsByLemmaCache.get(lemma) ?? [];
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

export function createCard(
  lemma: string,
  senseId: string,
  entryType: "word" | "phrase" = "word",
): SRSCard {
  const baseCard = createEmptyCard();
  const card: SRSCard = {
    ...baseCard,
    lemma,
    sense_id: senseId,
    entry_type: entryType,
  };
  return normalizeCardForStorage(card);
}

export function ensureCard(
  lemma: string,
  senseId: string,
  entryType: "word" | "phrase" = "word",
): SRSCard {
  const key = createCardKey(lemma, senseId);
  let card = cardsCache.get(key);
  if (!card) {
    card = createCard(lemma, senseId, entryType);
    cardsCache.set(key, card);
    addToLemmaIndex(card);
    dirtyCardKeys.add(key);
    scheduleSave();
  }
  return card;
}

export function updateCard(card: SRSCard): void {
  const normalized = normalizeCardForStorage(card);
  const key = createCardKey(normalized.lemma, normalized.sense_id);
  cardsCache.set(key, normalized);
  addToLemmaIndex(normalized);
  dirtyCardKeys.add(key);
  void setLastUpdated(Date.now()).catch(() => {});
  scheduleSave();
  notifyDataChange();
}

export async function setAllCards(cards: SRSCard[]): Promise<void> {
  const database = await getDB();
  const tx = database.transaction(CARDS_STORE, "readwrite");
  const store = tx.objectStore(CARDS_STORE);
  await store.clear();
  cardsCache.clear();
  cardsByLemmaCache.clear();
  for (const card of cards) {
    const normalized = normalizeCardForStorage(card);
    cardsCache.set(createCardKey(normalized.lemma, normalized.sense_id), normalized);
    await store.put(normalized);
  }
  await tx.done;
  rebuildLemmaIndex(Array.from(cardsCache.values()));
  dirtyCardKeys = new Set();
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
    void saveNow();
    saveDebounceTimer = null;
  }, SAVE_DEBOUNCE_MS);
}

async function saveCard(database: IDBPDatabase<SRSDatabase>, card: SRSCard): Promise<void> {
  const tx = database.transaction(CARDS_STORE, "readwrite");
  const store = tx.objectStore(CARDS_STORE);
  await store.put(normalizeCardForStorage(card));
  await tx.done;
}

async function saveDirtyCards(): Promise<void> {
  if (dirtyCardKeys.size === 0) return;

  const database = await getDB();

  while (dirtyCardKeys.size > 0) {
    const keys = [...dirtyCardKeys];
    dirtyCardKeys = new Set();

    for (const key of keys) {
      const card = cardsCache.get(key);
      if (!card) continue;

      try {
        await saveCard(database, card);
      } catch (err) {
        try {
          const stripped = normalizeCardForStorage({ ...card, skills: undefined });
          await saveCard(database, stripped);
          cardsCache.set(key, stripped);
          addToLemmaIndex(stripped);
        } catch {
          console.warn("Failed to persist SRS card", {
            lemma: card.lemma,
            sense_id: card.sense_id,
            err,
          });
        }
      }
    }
  }
}

export async function saveNow(): Promise<void> {
  saveChain = saveChain
    .then(() => saveDirtyCards())
    .catch(async (err) => {
      console.warn("SRS save failed", err);
      try {
        await saveDirtyCards();
      } catch (err2) {
        console.warn("SRS save retry failed", err2);
      }
    });
  return saveChain;
}

export async function forceSave(): Promise<void> {
  if (saveDebounceTimer) {
    clearTimeout(saveDebounceTimer);
    saveDebounceTimer = null;
  }
  dirtyCardKeys = new Set(cardsCache.keys());
  await saveNow();
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
  cardsByLemmaCache.clear();
}

export function getCacheSize(): number {
  return cardsCache.size;
}

export function hasCardForLemma(lemma: string): boolean {
  return cardsByLemmaCache.has(lemma);
}

export function getPrimaryCard(lemma: string): SRSCard | undefined {
  const cards = getCardsByLemma(lemma);
  return cards[0];
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
  const primaryCard = getPrimaryCard(lemma);
  if (!primaryCard) return false;
  return primaryCard.reps >= 3;
}

export function getSkillState(
  lemma: string,
  senseId: string,
  skillType: SkillType,
): SkillState | undefined {
  const card = getCard(lemma, senseId);
  return card?.skills?.[skillType];
}

export function updateSkillState(
  lemma: string,
  senseId: string,
  skillType: SkillType,
  skillState: SkillState,
): void {
  const card = getCard(lemma, senseId);
  if (!card) return;

  const updatedCard: SRSCard = {
    ...card,
    skills: {
      ...card.skills,
      [skillType]: skillState,
    },
  };

  updateCard(updatedCard);
}

export function getCardsWithDueSkills(now: Date = new Date()): {
  card: SRSCard;
  skillType: SkillType;
  skillState: SkillState;
}[] {
  const results: { card: SRSCard; skillType: SkillType; skillState: SkillState }[] = [];

  for (const card of getAllCards()) {
    if (!card.skills) continue;

    for (const [skill, state] of Object.entries(card.skills)) {
      if (state && new Date(state.due) <= now) {
        results.push({
          card,
          skillType: skill as SkillType,
          skillState: state,
        });
      }
    }
  }

  return results;
}

export function getNewSkillsForCard(card: SRSCard): SkillType[] {
  const unlockedSkills = getUnlockedSkills(card.stability);
  const existingSkills = card.skills ? Object.keys(card.skills) : [];

  return unlockedSkills.filter(
    (skill) => !existingSkills.includes(skill),
  );
}

export async function migratePrimarySenseIds(
  getEntry: (lemma: string) => Promise<SRSEligibleEntry | undefined>,
): Promise<number> {
  const cards = getAllCards();
  if (cards.length === 0) return 0;

  const uniqueLemmas = [...new Set(cards.map((c) => c.lemma))];
  const entryMap = new Map<string, SRSEligibleEntry>();
  const orphanedLemmas: string[] = [];

  for (const lemma of uniqueLemmas) {
    const entry = await getEntry(lemma);
    if (entry && entry.senses && entry.senses.length > 0) {
      entryMap.set(lemma, entry);
    } else {
      orphanedLemmas.push(lemma);
    }
  }

  const cardsToDelete: SRSCard[] = [];
  const cardsToMigrate: Array<{ oldCard: SRSCard; newSenseId: string }> = [];

  for (const lemma of orphanedLemmas) {
    const lemmaCards = cards.filter((c) => c.lemma === lemma);
    cardsToDelete.push(...lemmaCards);
  }

  for (const lemma of uniqueLemmas) {
    const entry = entryMap.get(lemma);
    if (!entry) continue;

    const primarySenseId = getPrimarySenseId(entry);
    const lemmaCards = cards.filter((c) => c.lemma === lemma);
    const hasPrimaryCard = lemmaCards.some((c) => c.sense_id === primarySenseId);

    for (const card of lemmaCards) {
      if (card.sense_id === primarySenseId) {
        continue;
      }

      if (hasPrimaryCard) {
        cardsToDelete.push(card);
      } else {
        cardsToMigrate.push({ oldCard: card, newSenseId: primarySenseId });
      }
    }
  }

  if (cardsToDelete.length === 0 && cardsToMigrate.length === 0) return 0;

  const database = await getDB();

  const orphanedLogs: SRSReviewLog[] = [];
  for (const lemma of orphanedLemmas) {
    const logs = await database.getAllFromIndex(LOGS_STORE, "lemma", lemma);
    orphanedLogs.push(...logs);
  }

  const tx = database.transaction([CARDS_STORE, LOGS_STORE], "readwrite");
  const cardsStore = tx.objectStore(CARDS_STORE);
  const logsStore = tx.objectStore(LOGS_STORE);

  for (const card of cardsToDelete) {
    cardsStore.delete([card.lemma, card.sense_id]);
  }

  for (const log of orphanedLogs) {
    logsStore.delete([log.lemma, log.sense_id, log.review]);
  }

  for (const { oldCard, newSenseId } of cardsToMigrate) {
    cardsStore.delete([oldCard.lemma, oldCard.sense_id]);
    const newCard: SRSCard = { ...oldCard, sense_id: newSenseId };
    cardsStore.put(newCard);
  }

  await tx.done;

  for (const card of cardsToDelete) {
    cardsCache.delete(createCardKey(card.lemma, card.sense_id));
    removeFromLemmaIndex(card.lemma, card.sense_id);
  }

  for (const { oldCard, newSenseId } of cardsToMigrate) {
    cardsCache.delete(createCardKey(oldCard.lemma, oldCard.sense_id));
    removeFromLemmaIndex(oldCard.lemma, oldCard.sense_id);
    const newCard: SRSCard = { ...oldCard, sense_id: newSenseId };
    cardsCache.set(createCardKey(newCard.lemma, newCard.sense_id), newCard);
    addToLemmaIndex(newCard);
  }

  return cardsToDelete.length + cardsToMigrate.length;
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

export async function fixCardEntryTypes(
  getWord: (lemma: string) => Promise<any | undefined>,
  getPhrase: (lemma: string) => Promise<any | undefined>,
): Promise<number> {
  const cards = getAllCards();
  const cardsToFix: SRSCard[] = [];

  // First pass: check all cards and collect which ones need fixing
  for (const card of cards) {
    const word = await getWord(card.lemma);
    const phrase = await getPhrase(card.lemma);

    let correctType: "word" | "phrase";
    if (phrase) {
      correctType = "phrase";
    } else if (word) {
      correctType = "word";
    } else {
      continue;
    }

    if (card.entry_type !== correctType) {
      cardsToFix.push({ ...card, entry_type: correctType });
    }
  }

  if (cardsToFix.length === 0) {
    return 0;
  }

  // Second pass: update all cards in a single transaction
  const database = await getDB();
  const tx = database.transaction(CARDS_STORE, "readwrite");
  const store = tx.objectStore(CARDS_STORE);

  for (const fixedCard of cardsToFix) {
    await store.put(fixedCard);
    cardsCache.set(createCardKey(fixedCard.lemma, fixedCard.sense_id), fixedCard);
    addToLemmaIndex(fixedCard);
  }

  await tx.done;
  notifyDataChange();
  return cardsToFix.length;
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
  rebuildLemmaIndex(snapshot.cards);

  notifyDataChange();
}

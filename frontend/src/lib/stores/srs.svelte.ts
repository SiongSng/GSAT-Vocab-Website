import { browser } from '$app/environment';
import { safeGetItem, safeSetItem } from '$lib/utils/safe-storage';
import { FSRS, Rating, State, type RecordLog } from "ts-fsrs";
import {
  initStorage,
  getCard,
  getAllCards,
  getDueCards,
  getNewCards,
  getLearningCards,
  getReviewCards,
  ensureCard,
  updateCard,
  addReviewLog,
  saveNow,
  forceSave,
  hasCardForLemma,
  getCardsByLemma,
  getNextUnlockableSense,
  updateDailyStats,
  addSessionLog,
  migratePrimarySenseIds,
  fixCardEntryTypes,
} from "./srs-storage";
import { STORAGE_KEYS } from "$lib/storage-keys";
import type {
  SRSCard,
  SRSReviewLog,
  DeckStats,
  StudySessionStats,
  DailyLimits,
  SRSEligibleEntry,
} from "$lib/types/srs";
import { isWordEntry } from "$lib/types/vocab";
import { DEFAULT_DAILY_LIMITS, getPrioritizedSenses } from "$lib/types/srs";
import { preloadAudio } from "$lib/tts";
import type { VocabEntry, VocabSense } from "$lib/types/vocab";

export { Rating, State };

const fsrs = new FSRS({});

interface SRSStore {
  initialized: boolean;
  isStudying: boolean;
  currentCard: SRSCard | null;
  currentSense: VocabSense | null;
  currentCardIndex: number;
  studyQueue: SRSCard[];
  isFlipped: boolean;
  schedulingInfo: RecordLog | null;
  sessionStats: StudySessionStats;
  dailyLimits: DailyLimits;
  newCardsStudiedToday: number;
  reviewsToday: number;
  statsVersion: number;
  sessionId: string | null;
  cramMode: boolean;
}

const store: SRSStore = $state({
  initialized: false,
  isStudying: false,
  currentCard: null,
  currentSense: null,
  currentCardIndex: 0,
  studyQueue: [],
  isFlipped: false,
  schedulingInfo: null,
  sessionStats: createEmptySessionStats(),
  dailyLimits: { ...DEFAULT_DAILY_LIMITS },
  newCardsStudiedToday: 0,
  reviewsToday: 0,
  statsVersion: 0,
  sessionId: null,
  cramMode: false,
});

function createEmptySessionStats(): StudySessionStats {
  return {
    cardsStudied: 0,
    againCount: 0,
    hardCount: 0,
    goodCount: 0,
    easyCount: 0,
    startTime: new Date(),
  };
}

function countTrueNewCards(): number {
  const allNewCards = getNewCards();
  const counted = new Set<string>();

  for (const card of allNewCards) {
    if (counted.has(card.lemma)) continue;
    const cardsForLemma = getCardsByLemma(card.lemma);
    const hasLearnedCards = cardsForLemma.some((c) => c.state !== State.New);
    if (!hasLearnedCards) {
      counted.add(card.lemma);
    }
  }

  return counted.size;
}

function countUnlockedSecondarySenses(): number {
  const allNewCards = getNewCards();
  let count = 0;

  for (const card of allNewCards) {
    const cardsForLemma = getCardsByLemma(card.lemma);
    if (cardsForLemma.length <= 1) continue;
    const hasLearnedCards = cardsForLemma.some((c) => c.state !== State.New);
    if (hasLearnedCards) {
      count++;
    }
  }

  return count;
}

const deckStats = $derived.by<DeckStats>(() => {
  void store.statsVersion;
  if (!store.initialized) {
    return {
      newCount: 0,
      learningCount: 0,
      reviewCount: 0,
      relearningCount: 0,
      totalDue: 0,
    };
  }
  return {
    newCount: countTrueNewCards(),
    learningCount: getLearningCards().length + countUnlockedSecondarySenses(),
    reviewCount: getReviewCards().length,
    relearningCount: getAllCards().filter((c) => c.state === State.Relearning).length,
    totalDue: getDueCards().length,
  };
});

export function getSRSStore() {
  return {
    get initialized() {
      return store.initialized;
    },
    get isStudying() {
      return store.isStudying;
    },
    get currentCard() {
      return store.currentCard;
    },
    get currentSense() {
      return store.currentSense;
    },
    get currentCardIndex() {
      return store.currentCardIndex;
    },
    get studyQueue() {
      return store.studyQueue;
    },
    get isFlipped() {
      return store.isFlipped;
    },
    get schedulingInfo() {
      return store.schedulingInfo;
    },
    get sessionStats() {
      return store.sessionStats;
    },
    get dailyLimits() {
      return store.dailyLimits;
    },
    get deckStats() {
      return deckStats;
    },
    get progress() {
      return {
        current: store.currentCardIndex + 1,
        total: store.studyQueue.length,
      };
    },
    get isComplete() {
      return (
        store.isStudying &&
        store.currentCardIndex >= store.studyQueue.length &&
        store.studyQueue.length > 0
      );
    },
    get cramMode() {
      return store.cramMode;
    },
  };
}

export async function initSRS(): Promise<void> {
  if (store.initialized) return;
  await initStorage();
  loadDailyProgress();
  store.initialized = true;
}

export async function runSRSEntryTypeFix(
  getWord: (lemma: string) => Promise<any | undefined>,
  getPhrase: (lemma: string) => Promise<any | undefined>,
): Promise<number> {
  if (!store.initialized) {
    await initSRS();
  }
  return fixCardEntryTypes(getWord, getPhrase);
}

export async function runSRSSenseMigration(
  getEntry: (lemma: string) => Promise<SRSEligibleEntry | undefined>,
): Promise<number> {
  if (!store.initialized) {
    await initSRS();
  }
  const migrated = await migratePrimarySenseIds(getEntry);
  if (migrated > 0) {
    store.statsVersion++;
  }
  return migrated;
}

export async function ensureSecondarySensesForUnlockedLemmas(
  getEntry: (lemma: string) => Promise<SRSEligibleEntry | undefined>,
): Promise<number> {
  if (!store.initialized) {
    await initSRS();
  }

  const lemmasWithCards = new Set(getAllCards().map((c) => c.lemma));
  let createdCount = 0;

  for (const lemma of lemmasWithCards) {
    const entry = await getEntry(lemma);
    if (!entry) continue;

    const prioritizedSenses = getPrioritizedSenses(entry);
    if (prioritizedSenses.length <= 1) continue;

    const prioritizedSenseIds = prioritizedSenses.map((p) => p.sense.sense_id);
    const entryType = isWordEntry(entry) ? "word" : "phrase";

    let next = getNextUnlockableSense(lemma, prioritizedSenseIds);
    while (next !== null) {
      const { created } = ensureCard(lemma, next.senseId, entryType);
      if (created) createdCount++;
      next = getNextUnlockableSense(lemma, prioritizedSenseIds);
    }
  }

  if (createdCount > 0) {
    store.statsVersion++;
    await forceSave();
  }

  return createdCount;
}

function loadDailyProgress(): void {
  if (!browser) return;
  const today = getTodayKey();
  try {
    const saved = safeGetItem(STORAGE_KEYS.DAILY_STUDIED(today));
    if (saved) {
      const data = JSON.parse(saved);
      store.newCardsStudiedToday = data.newCards || 0;
      store.reviewsToday = data.reviews || 0;
    } else {
      store.newCardsStudiedToday = 0;
      store.reviewsToday = 0;
    }
  } catch {
    store.newCardsStudiedToday = 0;
    store.reviewsToday = 0;
  }
}

function saveDailyProgress(): void {
  if (!browser) return;
  const today = getTodayKey();
  try {
    safeSetItem(
      STORAGE_KEYS.DAILY_STUDIED(today),
      JSON.stringify({
        newCards: store.newCardsStudiedToday,
        reviews: store.reviewsToday,
      }),
    );
  } catch {
    // ignore
  }
}

function getTodayKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function addWordToSRS(lemma: string, senseId: string): void {
  ensureCard(lemma, senseId);
}

export function addEntryToSRS(entry: SRSEligibleEntry): void {
  const prioritizedSenses = getPrioritizedSenses(entry);
  const entryType = isWordEntry(entry) ? "word" : "phrase";

  if (prioritizedSenses.length === 0) {
    return;
  }

  // Only add the primary sense initially
  const primarySense = prioritizedSenses[0].sense;
  ensureCard(entry.lemma, primarySense.sense_id, entryType);
}

export function ensureEntryCard(entry: SRSEligibleEntry): SRSCard | null {
  const prioritizedSenses = getPrioritizedSenses(entry);
  const entryType = isWordEntry(entry) ? "word" : "phrase";

  if (prioritizedSenses.length === 0) {
    return null;
  }

  const primarySense = prioritizedSenses[0].sense;
  return ensureCard(entry.lemma, primarySense.sense_id, entryType).card;
}

export function addEntriesToSRS(entries: SRSEligibleEntry[]): void {
  for (const entry of entries) {
    addEntryToSRS(entry);
  }
}

export function addWordWithAllSenses(entry: VocabEntry): void {
  const prioritizedSenses = getPrioritizedSenses(entry);
  const entryType = isWordEntry(entry) ? "word" : "phrase";

  if (prioritizedSenses.length === 0) {
    return;
  }
  for (const { sense } of prioritizedSenses) {
    ensureCard(entry.lemma, sense.sense_id, entryType);
  }
}

export function addWordsWithAllSenses(entries: VocabEntry[]): void {
  for (const entry of entries) {
    addWordWithAllSenses(entry);
  }
}

export function addSenseToSRS(
  lemma: string,
  senseId: string,
  entryType: "word" | "phrase" = "word",
): void {
  ensureCard(lemma, senseId, entryType);
}

function getEligibleNewCards(
  excludeSet: Set<string>,
  selectionPool?: string[],
): SRSCard[] {
  if (selectionPool && selectionPool.length > 0) {
    const result: SRSCard[] = [];
    for (const lemma of selectionPool) {
      if (excludeSet.has(lemma)) continue;
      const cardsForLemma = getCardsByLemma(lemma);
      if (cardsForLemma.length === 0) continue;

      const newCards = cardsForLemma.filter((c) => c.state === State.New);
      if (newCards.length === 0) continue;

      const hasLearnedCards = cardsForLemma.some((c) => c.state !== State.New);
      if (hasLearnedCards) continue;

      result.push(newCards[0]);
    }
    return result;
  }

  const allNewCards = getNewCards();
  const cardMap = new Map<string, SRSCard>();

  for (const card of allNewCards) {
    if (excludeSet.has(card.lemma)) continue;
    if (cardMap.has(card.lemma)) continue;

    const cardsForLemma = getCardsByLemma(card.lemma);
    const hasLearnedCards = cardsForLemma.some((c) => c.state !== State.New);
    if (hasLearnedCards) continue;

    cardMap.set(card.lemma, card);
  }

  return Array.from(cardMap.values());
}

function getUnlockedSecondarySenseCards(excludeSet: Set<string>): SRSCard[] {
  const allNewCards = getNewCards();
  const result: SRSCard[] = [];

  for (const card of allNewCards) {
    if (excludeSet.has(card.lemma)) continue;

    const cardsForLemma = getCardsByLemma(card.lemma);
    if (cardsForLemma.length <= 1) continue;

    const hasLearnedCards = cardsForLemma.some((c) => c.state !== State.New);
    if (!hasLearnedCards) continue;

    result.push(card);
  }

  return result;
}

export type StudyPriority = "mixed" | "new_first" | "review_first";

export interface SessionOptions {
  newLimit: number;
  reviewLimit?: number;
  selectionPool?: string[];
  newCards?: SRSCard[];
  excludeLemmas?: Set<string>;
  priority?: StudyPriority;
  isCustomDeck?: boolean;
  cramMode?: boolean;
}

export interface SessionCardCounts {
  newCount: number;
  learningCount: number;
  reviewCount: number;
  total: number;
}

interface SessionCards {
  newCards: SRSCard[];
  learningCards: SRSCard[];
  reviewCards: SRSCard[];
}

function selectSessionCards(options: SessionOptions): SessionCards {
  const now = new Date();
  const excludeSet = options.excludeLemmas ?? new Set();
  const isCustomDeck = options.isCustomDeck ?? false;

  const reviewLimit = isCustomDeck
    ? Infinity
    : (options.reviewLimit ?? Infinity);

  const baseLearningCards = getLearningCards().filter(
    (c) => new Date(c.due) <= now && !excludeSet.has(c.lemma),
  );

  const secondarySenseCards = getUnlockedSecondarySenseCards(excludeSet);
  const learningCards = [...baseLearningCards, ...secondarySenseCards];

  const reviewCards = getReviewCards(now)
    .filter((c) => !excludeSet.has(c.lemma))
    .slice(0, reviewLimit === Infinity ? undefined : reviewLimit);

  const newCards = options.newCards
    ? options.newCards.slice(0, options.newLimit)
    : getEligibleNewCards(excludeSet, options.selectionPool).slice(0, options.newLimit);

  return { newCards, learningCards, reviewCards };
}

export function getSessionCardCounts(
  options: SessionOptions,
): SessionCardCounts {
  const { newCards, learningCards, reviewCards } = selectSessionCards(options);
  return {
    newCount: newCards.length,
    learningCount: learningCards.length,
    reviewCount: reviewCards.length,
    total: newCards.length + learningCards.length + reviewCards.length,
  };
}

function shuffleArray<T>(array: T[]): void {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}

function buildStudyQueue(
  cards: SessionCards,
  priority: StudyPriority,
): SRSCard[] {
  const { newCards, learningCards, reviewCards } = cards;

  shuffleArray(newCards);
  shuffleArray(learningCards);
  shuffleArray(reviewCards);

  switch (priority) {
    case "new_first":
      return [...newCards, ...learningCards, ...reviewCards];
    case "review_first":
      return [...learningCards, ...reviewCards, ...newCards];
    case "mixed":
    default: {
      const reviewPart = [...learningCards, ...reviewCards];
      return interleaveCards(reviewPart, newCards);
    }
  }
}

function interleaveCards<T>(reviewCards: T[], newCards: T[]): T[] {
  if (newCards.length === 0) return reviewCards;
  if (reviewCards.length === 0) return newCards;

  const result: T[] = [];
  const ratio = reviewCards.length / newCards.length;

  let reviewIdx = 0;
  let newIdx = 0;

  while (reviewIdx < reviewCards.length || newIdx < newCards.length) {
    if (reviewIdx < reviewCards.length) {
      const reviewsToAdd = Math.max(1, Math.round(ratio));
      for (let i = 0; i < reviewsToAdd && reviewIdx < reviewCards.length; i++) {
        result.push(reviewCards[reviewIdx++]);
      }
    }

    if (newIdx < newCards.length) {
      result.push(newCards[newIdx++]);
    }
  }

  return result;
}

export function startStudySession(options: SessionOptions): void {
  const cramMode = options.cramMode ?? false;
  let queue: SRSCard[];

  if (cramMode) {
    const excludeSet = options.excludeLemmas ?? new Set();
    const allCards = getAllCards().filter((c) => !excludeSet.has(c.lemma));

    const seen = new Map<string, SRSCard>();
    for (const card of allCards) {
      if (!seen.has(card.lemma)) {
        seen.set(card.lemma, card);
      }
    }
    queue = Array.from(seen.values());
    shuffleArray(queue);
  } else {
    const cards = selectSessionCards(options);
    const priority = options.priority ?? "mixed";
    queue = buildStudyQueue(cards, priority);
  }

  store.studyQueue = queue;
  store.currentCardIndex = 0;
  store.isStudying = true;
  store.isFlipped = false;
  store.sessionStats = createEmptySessionStats();
  store.sessionId = crypto.randomUUID?.() ?? `session-${Date.now()}`;
  store.cramMode = cramMode;

  if (queue.length > 0) {
    setCurrentCard(queue[0]);
  } else {
    store.currentCard = null;
    store.currentSense = null;
    store.schedulingInfo = null;
  }
}

const PRELOAD_AHEAD = 3;
let preloadTimer: ReturnType<typeof setTimeout> | undefined;

function preloadUpcomingAudio(): void {
  clearTimeout(preloadTimer);

  preloadTimer = setTimeout(() => {
    if (!store.isStudying) return;

    const startIdx = store.currentCardIndex + 1;
    const endIdx = Math.min(startIdx + PRELOAD_AHEAD, store.studyQueue.length);

    if (startIdx < endIdx) {
      const lemmas = store.studyQueue
        .slice(startIdx, endIdx)
        .map((c) => c.lemma);
      preloadAudio(lemmas);
    }
  }, 1200);
}

function setCurrentCard(card: SRSCard): void {
  store.currentCard = card;
  store.currentSense = null;
  store.isFlipped = false;
  computeSchedulingInfo(card);
  preloadUpcomingAudio();
}

export function setCurrentSense(sense: VocabSense | null): void {
  store.currentSense = sense;
}

function computeSchedulingInfo(card: SRSCard): void {
  const now = new Date();
  const scheduling = fsrs.repeat(card, now);
  store.schedulingInfo = scheduling;
}

export function flipCard(): void {
  store.isFlipped = !store.isFlipped;
}

export function showAnswer(): void {
  store.isFlipped = true;
}

export function rateCard(rating: Rating): void {
  if (!store.currentCard || !store.schedulingInfo) return;
  if (rating === Rating.Manual) return;

  const recordLog = store.schedulingInfo[rating];
  if (!recordLog) return;

  if (store.cramMode) {
    store.sessionStats.cardsStudied++;
    moveToNextCard();
    return;
  }

  const { card: newCard, log } = recordLog;

  const wasNew = store.currentCard.state === State.New;
  const wasReview = store.currentCard.state === State.Review;

  const existingCard = getCard(store.currentCard.lemma, store.currentCard.sense_id);

  const updatedCard: SRSCard = {
    ...newCard,
    lemma: store.currentCard.lemma,
    sense_id: store.currentCard.sense_id,
    entry_type: store.currentCard.entry_type,
    skills: existingCard?.skills,
  };

  updateCard(updatedCard);
  store.statsVersion++;

  store.sessionStats.cardsStudied++;
  switch (rating) {
    case Rating.Again:
      store.sessionStats.againCount++;
      break;
    case Rating.Hard:
      store.sessionStats.hardCount++;
      break;
    case Rating.Good:
      store.sessionStats.goodCount++;
      break;
    case Rating.Easy:
      store.sessionStats.easyCount++;
      break;
  }

  if (wasNew) {
    store.newCardsStudiedToday++;
    saveDailyProgress();
  } else if (wasReview) {
    store.reviewsToday++;
    saveDailyProgress();
  }

  if (rating === Rating.Again) {
    store.studyQueue.push(updatedCard);
  }

  moveToNextCard();

  const reviewLog: SRSReviewLog = {
    ...log,
    lemma: updatedCard.lemma,
    sense_id: updatedCard.sense_id,
  };

  void saveNow();
  void addReviewLog(reviewLog).catch(() => {});
  void updateDailyStats(rating, wasNew).catch(() => {});
}

function moveToNextCard(): void {
  store.currentCardIndex++;

  if (store.currentCardIndex < store.studyQueue.length) {
    const nextCard = store.studyQueue[store.currentCardIndex];
    const freshCard = getCard(nextCard.lemma, nextCard.sense_id) || nextCard;
    setCurrentCard(freshCard);
  } else {
    store.currentCard = null;
    store.currentSense = null;
    store.schedulingInfo = null;
    store.sessionStats.endTime = new Date();
  }
}

export async function endStudySession(): Promise<void> {
  clearTimeout(preloadTimer);
  if (
    store.sessionId &&
    store.sessionStats.cardsStudied > 0 &&
    !store.cramMode
  ) {
    try {
      const startTime = store.sessionStats.startTime.getTime();
      const endTime = Date.now();
      await addSessionLog(
        store.sessionId,
        startTime,
        endTime,
        store.sessionStats.cardsStudied,
      );
    } catch {
      // ignore
    }
  }

  store.isStudying = false;
  store.currentCard = null;
  store.currentSense = null;
  store.studyQueue = [];
  store.currentCardIndex = 0;
  store.isFlipped = false;
  store.schedulingInfo = null;
  store.sessionId = null;
  store.cramMode = false;
  store.statsVersion++;
  try {
    await saveNow();
  } catch {
    // ignore
  }
}

export function getIntervalText(rating: Rating): string {
  if (!store.schedulingInfo) return "";
  if (rating === Rating.Manual) return "";

  const recordLog = store.schedulingInfo[rating];
  if (!recordLog) return "";

  const due = new Date(recordLog.card.due);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();

  if (diffMs < 0) return "now";

  const diffMinutes = Math.round(diffMs / (1000 * 60));
  const diffHours = Math.round(diffMs / (1000 * 60 * 60));
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffMinutes < 60) return `${diffMinutes}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 30) return `${diffDays}d`;
  if (diffDays < 365) return `${Math.round(diffDays / 30)}mo`;
  return `${Math.round(diffDays / 365)}y`;
}

export function setDailyLimits(limits: Partial<DailyLimits>): void {
  store.dailyLimits = { ...store.dailyLimits, ...limits };
  if (!browser) return;
  try {
    safeSetItem(
      STORAGE_KEYS.DAILY_LIMITS,
      JSON.stringify(store.dailyLimits),
    );
  } catch {
    // ignore
  }
}

export function loadDailyLimits(): void {
  if (!browser) return;
  try {
    const saved = safeGetItem(STORAGE_KEYS.DAILY_LIMITS);
    if (saved) {
      store.dailyLimits = { ...DEFAULT_DAILY_LIMITS, ...JSON.parse(saved) };
    }
  } catch {
    // ignore
  }
}

export function getRemainingNewCards(): number {
  return Math.max(0, store.dailyLimits.newCards - store.newCardsStudiedToday);
}

export function getRemainingReviews(): number {
  return Math.max(0, store.dailyLimits.reviews - store.reviewsToday);
}

export function getUniqueLemmaCount(): number {
  const lemmas = new Set<string>();
  for (const card of getAllCards()) {
    lemmas.add(card.lemma);
  }
  return lemmas.size;
}

export function getCardsForLemma(lemma: string): SRSCard[] {
  return getCardsByLemma(lemma);
}

export function getLemmaHasCard(lemma: string): boolean {
  return hasCardForLemma(lemma);
}

export function findSenseForCard(
  card: SRSCard,
  entry: VocabEntry | null,
): VocabSense | null {
  if (!entry || !entry.senses || entry.senses.length === 0) return null;

  const prioritized = getPrioritizedSenses(entry);
  if (prioritized.length === 0) return entry.senses[0];

  if (card.sense_id === "primary") {
    return prioritized[0].sense;
  }

  const found = prioritized.find((p) => p.sense.sense_id === card.sense_id);
  return found?.sense || prioritized[0].sense;
}

export function getSenseIndex(
  entry: VocabEntry | null,
  senseId: string,
): number {
  if (!entry || !entry.senses) return 0;

  const prioritized = getPrioritizedSenses(entry);
  if (prioritized.length === 0) return 0;

  if (senseId === "primary") return 0;

  const idx = prioritized.findIndex((p) => p.sense.sense_id === senseId);
  return idx >= 0 ? idx : 0;
}

export function tryUnlockNextSense(entry: SRSEligibleEntry): SRSCard | null {
  const prioritizedSenses = getPrioritizedSenses(entry);
  if (prioritizedSenses.length <= 1) return null;

  const prioritizedSenseIds = prioritizedSenses.map((p) => p.sense.sense_id);
  const next = getNextUnlockableSense(entry.lemma, prioritizedSenseIds);

  if (next === null) return null;

  const entryType = isWordEntry(entry) ? "word" : "phrase";
  const { card: newCard } = ensureCard(entry.lemma, next.senseId, entryType);
  store.statsVersion++;

  return newCard;
}

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
  forceSave,
  hasCardForLemma,
  getCardsByLemma,
  shouldUnlockSecondarySenses,
  updateDailyStats,
  addSessionLog,
} from "./srs-storage";
import type {
  SRSCard,
  SRSReviewLog,
  DeckStats,
  StudySessionStats,
  DailyLimits,
} from "$lib/types/srs";
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

const deckStats = $derived<DeckStats>({
  newCount:
    store.initialized && store.statsVersion >= 0 ? getNewCards().length : 0,
  learningCount:
    store.initialized && store.statsVersion >= 0
      ? getLearningCards().length
      : 0,
  reviewCount:
    store.initialized && store.statsVersion >= 0 ? getReviewCards().length : 0,
  relearningCount:
    store.initialized && store.statsVersion >= 0
      ? getAllCards().filter((c) => c.state === State.Relearning).length
      : 0,
  totalDue:
    store.initialized && store.statsVersion >= 0 ? getDueCards().length : 0,
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
  };
}

export async function initSRS(): Promise<void> {
  if (store.initialized) return;
  await initStorage();
  loadDailyProgress();
  store.initialized = true;
}

function loadDailyProgress(): void {
  const today = getTodayKey();
  try {
    const saved = localStorage.getItem(`gsat_srs_daily_${today}`);
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
  const today = getTodayKey();
  try {
    localStorage.setItem(
      `gsat_srs_daily_${today}`,
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

export function addWordToSRS(lemma: string, senseId: string = "primary"): void {
  ensureCard(lemma, senseId);
}

export function addWordsToSRS(lemmas: string[]): void {
  for (const lemma of lemmas) {
    ensureCard(lemma, "primary");
  }
}

export function addWordWithAllSenses(entry: VocabEntry): void {
  const prioritizedSenses = getPrioritizedSenses(entry);
  if (prioritizedSenses.length === 0) {
    ensureCard(entry.lemma, "primary");
    return;
  }
  for (const { sense } of prioritizedSenses) {
    ensureCard(entry.lemma, sense.sense_id);
  }
}

export function addWordsWithAllSenses(entries: VocabEntry[]): void {
  for (const entry of entries) {
    addWordWithAllSenses(entry);
  }
}

export function addSenseToSRS(lemma: string, senseId: string): void {
  ensureCard(lemma, senseId);
}

function getEligibleNewCards(
  excludeSet: Set<string>,
  orderedPool?: string[],
): SRSCard[] {
  const allNewCards = getNewCards();
  const cardMap = new Map<string, SRSCard[]>();

  for (const card of allNewCards) {
    if (excludeSet.has(card.lemma)) continue;

    const isPrimarySense =
      card.sense_id === "primary" ||
      !getCardsByLemma(card.lemma).some(
        (c) => c.sense_id === "primary" && c !== card,
      );

    const isEligible =
      isPrimarySense || shouldUnlockSecondarySenses(card.lemma);

    if (isEligible) {
      const existing = cardMap.get(card.lemma) || [];
      existing.push(card);
      cardMap.set(card.lemma, existing);
    }
  }

  if (orderedPool && orderedPool.length > 0) {
    const result: SRSCard[] = [];
    for (const lemma of orderedPool) {
      const cards = cardMap.get(lemma);
      if (cards) {
        result.push(...cards);
      }
    }
    return result;
  }

  return Array.from(cardMap.values()).flat();
}

export function startStudySession(options?: {
  newLimit?: number;
  reviewLimit?: number;
  newCardPool?: string[];
  excludeLemmas?: Set<string>;
}): void {
  const now = new Date();
  const queue: SRSCard[] = [];
  const excludeSet = options?.excludeLemmas ?? new Set();

  const newLimit =
    options?.newLimit ??
    Math.max(0, store.dailyLimits.newCards - store.newCardsStudiedToday);
  const reviewLimit =
    options?.reviewLimit ??
    Math.max(0, store.dailyLimits.reviews - store.reviewsToday);

  const learningCards = getLearningCards().filter(
    (c) => new Date(c.due) <= now && !excludeSet.has(c.lemma),
  );
  const reviewCards = getReviewCards(now)
    .filter((c) => !excludeSet.has(c.lemma))
    .slice(0, reviewLimit);

  const eligibleNewCards = getEligibleNewCards(
    excludeSet,
    options?.newCardPool,
  );
  const newCards = eligibleNewCards.slice(0, newLimit);

  queue.push(...learningCards);
  queue.push(...reviewCards);
  queue.push(...newCards);

  shuffleArray(queue);

  store.studyQueue = queue;
  store.currentCardIndex = 0;
  store.isStudying = true;
  store.isFlipped = false;
  store.sessionStats = createEmptySessionStats();
  store.sessionId = crypto.randomUUID?.() ?? `session-${Date.now()}`;

  if (queue.length > 0) {
    setCurrentCard(queue[0]);
  } else {
    store.currentCard = null;
    store.currentSense = null;
    store.schedulingInfo = null;
  }
}

const PRELOAD_AHEAD = 3;

function preloadUpcomingAudio(): void {
  const startIdx = store.currentCardIndex;
  const endIdx = Math.min(startIdx + PRELOAD_AHEAD, store.studyQueue.length);
  const lemmas = store.studyQueue.slice(startIdx, endIdx).map((c) => c.lemma);
  preloadAudio(lemmas);
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

export async function rateCard(rating: Rating): Promise<void> {
  if (!store.currentCard || !store.schedulingInfo) return;
  if (rating === Rating.Manual) return;

  const recordLog = store.schedulingInfo[rating];
  if (!recordLog) return;

  const { card: newCard, log } = recordLog;

  const wasNew = store.currentCard.state === State.New;
  const wasReview = store.currentCard.state === State.Review;

  const updatedCard: SRSCard = {
    ...newCard,
    lemma: store.currentCard.lemma,
    sense_id: store.currentCard.sense_id,
  };

  updateCard(updatedCard);

  const reviewLog: SRSReviewLog = {
    ...log,
    lemma: store.currentCard.lemma,
    sense_id: store.currentCard.sense_id,
  };
  await addReviewLog(reviewLog);

  await updateDailyStats(rating, wasNew);

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

  store.statsVersion++;
  moveToNextCard();
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
  if (store.sessionId && store.sessionStats.cardsStudied > 0) {
    const startTime = store.sessionStats.startTime.getTime();
    const endTime = Date.now();
    await addSessionLog(
      store.sessionId,
      startTime,
      endTime,
      store.sessionStats.cardsStudied,
    );
  }

  store.isStudying = false;
  store.currentCard = null;
  store.currentSense = null;
  store.studyQueue = [];
  store.currentCardIndex = 0;
  store.isFlipped = false;
  store.schedulingInfo = null;
  store.sessionId = null;
  store.statsVersion++;
  forceSave();
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
  try {
    localStorage.setItem("gsat_srs_limits", JSON.stringify(store.dailyLimits));
  } catch {
    // ignore
  }
}

export function loadDailyLimits(): void {
  try {
    const saved = localStorage.getItem("gsat_srs_limits");
    if (saved) {
      store.dailyLimits = { ...DEFAULT_DAILY_LIMITS, ...JSON.parse(saved) };
    }
  } catch {
    // ignore
  }
}

function shuffleArray<T>(array: T[]): void {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
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

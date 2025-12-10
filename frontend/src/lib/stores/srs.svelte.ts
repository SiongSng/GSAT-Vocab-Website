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
} from "./srs-storage";
import type {
  SRSCard,
  SRSReviewLog,
  DeckStats,
  StudySessionStats,
  DailyLimits,
} from "$lib/types/srs";
import { DEFAULT_DAILY_LIMITS } from "$lib/types/srs";
import { getAudioUrl } from "$lib/api";

export { Rating, State };

const fsrs = new FSRS({});

interface SRSStore {
  initialized: boolean;
  isStudying: boolean;
  currentCard: SRSCard | null;
  currentCardIndex: number;
  studyQueue: SRSCard[];
  isFlipped: boolean;
  schedulingInfo: RecordLog | null;
  sessionStats: StudySessionStats;
  dailyLimits: DailyLimits;
  newCardsStudiedToday: number;
  reviewsToday: number;
}

const store: SRSStore = $state({
  initialized: false,
  isStudying: false,
  currentCard: null,
  currentCardIndex: 0,
  studyQueue: [],
  isFlipped: false,
  schedulingInfo: null,
  sessionStats: createEmptySessionStats(),
  dailyLimits: { ...DEFAULT_DAILY_LIMITS },
  newCardsStudiedToday: 0,
  reviewsToday: 0,
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
  newCount: store.initialized ? getNewCards().length : 0,
  learningCount: store.initialized ? getLearningCards().length : 0,
  reviewCount: store.initialized ? getReviewCards().length : 0,
  relearningCount: store.initialized
    ? getAllCards().filter((c) => c.state === State.Relearning).length
    : 0,
  totalDue: store.initialized ? getDueCards().length : 0,
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

export function addWordsToSRS(lemmas: string[]): void {
  for (const lemma of lemmas) {
    ensureCard(lemma);
  }
}

export function startStudySession(options?: {
  newLimit?: number;
  reviewLimit?: number;
  customWords?: string[];
}): void {
  const now = new Date();
  const queue: SRSCard[] = [];

  if (options?.customWords && options.customWords.length > 0) {
    for (const lemma of options.customWords) {
      const card = ensureCard(lemma);
      queue.push(card);
    }
  } else {
    const newLimit =
      options?.newLimit ??
      store.dailyLimits.newCards - store.newCardsStudiedToday;
    const reviewLimit =
      options?.reviewLimit ?? store.dailyLimits.reviews - store.reviewsToday;

    const newCards = getNewCards().slice(0, Math.max(0, newLimit));
    const reviewCards = getReviewCards(now).slice(0, Math.max(0, reviewLimit));
    const learningCards = getLearningCards().filter(
      (c) => new Date(c.due) <= now,
    );

    queue.push(...learningCards);
    queue.push(...reviewCards);
    queue.push(...newCards);
  }

  shuffleArray(queue);

  store.studyQueue = queue;
  store.currentCardIndex = 0;
  store.isStudying = true;
  store.isFlipped = false;
  store.sessionStats = createEmptySessionStats();

  if (queue.length > 0) {
    setCurrentCard(queue[0]);
  } else {
    store.currentCard = null;
    store.schedulingInfo = null;
  }
}

function setCurrentCard(card: SRSCard): void {
  store.currentCard = card;
  store.isFlipped = false;
  computeSchedulingInfo(card);
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

  const recordLog = store.schedulingInfo[rating];
  if (!recordLog) return;

  const { card: newCard, log } = recordLog;

  const wasNew = store.currentCard.state === State.New;
  const wasReview = store.currentCard.state === State.Review;

  const updatedCard: SRSCard = {
    ...newCard,
    lemma: store.currentCard.lemma,
  };

  updateCard(updatedCard);

  const reviewLog: SRSReviewLog = {
    ...log,
    lemma: store.currentCard.lemma,
  };
  await addReviewLog(reviewLog);

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
}

function moveToNextCard(): void {
  store.currentCardIndex++;

  if (store.currentCardIndex < store.studyQueue.length) {
    const nextCard = store.studyQueue[store.currentCardIndex];
    const freshCard = getCard(nextCard.lemma) || nextCard;
    setCurrentCard(freshCard);
  } else {
    store.currentCard = null;
    store.schedulingInfo = null;
    store.sessionStats.endTime = new Date();
  }
}

export function endStudySession(): void {
  store.isStudying = false;
  store.currentCard = null;
  store.studyQueue = [];
  store.currentCardIndex = 0;
  store.isFlipped = false;
  store.schedulingInfo = null;
  forceSave();
}

export function getIntervalText(rating: Rating): string {
  if (!store.schedulingInfo) return "";

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

let audioPlayer: HTMLAudioElement | null = null;

export function playCurrentCardAudio(): void {
  if (!store.currentCard) return;
  if (!audioPlayer) {
    audioPlayer = new Audio();
  }
  audioPlayer.src = getAudioUrl(store.currentCard.lemma);
  audioPlayer.play().catch(() => {});
}

export function getRemainingNewCards(): number {
  return Math.max(0, store.dailyLimits.newCards - store.newCardsStudiedToday);
}

export function getRemainingReviews(): number {
  return Math.max(0, store.dailyLimits.reviews - store.reviewsToday);
}

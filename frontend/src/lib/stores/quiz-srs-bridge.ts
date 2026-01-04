import { Rating, State } from "ts-fsrs";
import type { QuizQuestionType } from "./quiz-generator";
import {
  getCard,
  ensureCard,
  updateCard,
  addReviewLog,
  updateDailyStats,
} from "./srs-storage";
import type { SRSCard, SRSReviewLog } from "$lib/types/srs";
import { FSRS } from "ts-fsrs";

export { Rating };

const fsrs = new FSRS({});

export interface QuizResult {
  lemma: string;
  sense_id: string;
  entry_type: "word" | "phrase";
  question_type: QuizQuestionType;
  correct: boolean;
  response_time_ms: number;
  used_hint: boolean;
}

const FAST_RESPONSE_MS = 5000;
const SLOW_RESPONSE_MS = 15000;

const HARD_QUESTION_TYPES: QuizQuestionType[] = [
  "spelling",
  "distinction",
  "fill_blank",
];

export function mapQuizResultToRating(result: QuizResult): Rating {
  if (!result.correct) {
    return Rating.Again;
  }

  if (result.used_hint) {
    return Rating.Hard;
  }

  if (result.response_time_ms > SLOW_RESPONSE_MS) {
    return Rating.Hard;
  }

  const isHardType = HARD_QUESTION_TYPES.includes(result.question_type);

  if (isHardType && result.response_time_ms < FAST_RESPONSE_MS) {
    return Rating.Easy;
  }

  return Rating.Good;
}

export function recordQuizResult(result: QuizResult): void {
  let card = getCard(result.lemma, result.sense_id);

  if (!card) {
    card = ensureCard(result.lemma, result.sense_id, result.entry_type);
  }

  const rating = mapQuizResultToRating(result);
  if (rating === Rating.Manual) return;

  const now = new Date();
  const wasNew = card.state === State.New;

  const scheduling = fsrs.repeat(card, now);
  const recordLog = scheduling[rating];

  if (!recordLog) return;

  const { card: newCard, log } = recordLog;

  const updatedCard: SRSCard = {
    ...newCard,
    lemma: card.lemma,
    sense_id: card.sense_id,
    entry_type: card.entry_type,
  };

  updateCard(updatedCard);

  const reviewLog: SRSReviewLog = {
    ...log,
    lemma: updatedCard.lemma,
    sense_id: updatedCard.sense_id,
  };

  queueMicrotask(() => {
    addReviewLog(reviewLog);
    updateDailyStats(rating, wasNew, result.response_time_ms);
  });
}

export function applyQuizSessionResults(results: QuizResult[]): void {
  for (const result of results) {
    recordQuizResult(result);
  }
}

export interface QuizSessionSummary {
  total: number;
  correct: number;
  incorrect: number;
  avgResponseTime: number;
  ratingBreakdown: {
    again: number;
    hard: number;
    good: number;
    easy: number;
  };
}

export function computeSessionSummary(results: QuizResult[]): QuizSessionSummary {
  const summary: QuizSessionSummary = {
    total: results.length,
    correct: 0,
    incorrect: 0,
    avgResponseTime: 0,
    ratingBreakdown: {
      again: 0,
      hard: 0,
      good: 0,
      easy: 0,
    },
  };

  if (results.length === 0) return summary;

  let totalTime = 0;

  for (const result of results) {
    if (result.correct) {
      summary.correct++;
    } else {
      summary.incorrect++;
    }

    totalTime += result.response_time_ms;

    const rating = mapQuizResultToRating(result);
    switch (rating) {
      case Rating.Again:
        summary.ratingBreakdown.again++;
        break;
      case Rating.Hard:
        summary.ratingBreakdown.hard++;
        break;
      case Rating.Good:
        summary.ratingBreakdown.good++;
        break;
      case Rating.Easy:
        summary.ratingBreakdown.easy++;
        break;
    }
  }

  summary.avgResponseTime = totalTime / results.length;

  return summary;
}

import {
  type Card as FSRSCard,
  type ReviewLog as FSRSReviewLog,
  State,
  Rating,
} from "ts-fsrs";
import type { VocabEntry, VocabSense } from "./vocab";

export { State, Rating };

export interface SRSCard extends FSRSCard {
  lemma: string;
  sense_id: string;
}

export interface SRSReviewLog extends FSRSReviewLog {
  lemma: string;
  sense_id: string;
}

export function createCardKey(lemma: string, senseId: string): string {
  return `${lemma}::${senseId}`;
}

export function parseCardKey(key: string): { lemma: string; sense_id: string } {
  const [lemma, sense_id] = key.split("::");
  return { lemma, sense_id: sense_id || "" };
}

export interface DeckStats {
  newCount: number;
  learningCount: number;
  reviewCount: number;
  relearningCount: number;
  totalDue: number;
}

export interface StudySessionStats {
  cardsStudied: number;
  againCount: number;
  hardCount: number;
  goodCount: number;
  easyCount: number;
  startTime: Date;
  endTime?: Date;
}

export interface DailyStats {
  date: string;
  new_cards: number;
  reviews: number;
  again: number;
  hard: number;
  good: number;
  easy: number;
  study_time_ms: number;
  updated_at: number;
}

export interface SessionLog {
  id?: number;
  session_id: string;
  start: number;
  end: number;
  studied: number;
}

export interface DailyLimits {
  newCards: number;
  reviews: number;
}

export const DEFAULT_DAILY_LIMITS: DailyLimits = {
  newCards: 20,
  reviews: 200,
};

export function stateToLabel(state: State): string {
  switch (state) {
    case State.New:
      return "New";
    case State.Learning:
      return "Learning";
    case State.Review:
      return "Review";
    case State.Relearning:
      return "Relearning";
    default:
      return "Unknown";
  }
}

export function ratingToLabel(rating: Rating): string {
  switch (rating) {
    case Rating.Again:
      return "Again";
    case Rating.Hard:
      return "Hard";
    case Rating.Good:
      return "Good";
    case Rating.Easy:
      return "Easy";
    default:
      return "Unknown";
  }
}

export interface PrioritizedSense {
  sense: VocabSense;
  priority: number;
  isPrimary: boolean;
}

export function getPrioritizedSenses(entry: VocabEntry): PrioritizedSense[] {
  if (!entry.senses || entry.senses.length === 0) return [];

  const sensesWithPriority = entry.senses.map((sense, originalIndex) => {
    const exampleCount = sense.examples?.length ?? 0;
    const testedBonus = sense.tested_in_exam ? 1 : 0;
    const priority =
      exampleCount * 1000 + testedBonus * 100 + (1000 - originalIndex);
    return { sense, priority, originalIndex };
  });

  sensesWithPriority.sort((a, b) => b.priority - a.priority);

  return sensesWithPriority.map((item, idx) => ({
    sense: item.sense,
    priority: idx,
    isPrimary: idx === 0,
  }));
}

export function getPrimarySenseId(entry: VocabEntry): string {
  const prioritized = getPrioritizedSenses(entry);
  return prioritized.length > 0 ? prioritized[0].sense.sense_id : "primary";
}

export function getSensePriorityIndex(
  entry: VocabEntry,
  senseId: string,
): number {
  const prioritized = getPrioritizedSenses(entry);
  const idx = prioritized.findIndex((p) => p.sense.sense_id === senseId);
  return idx >= 0 ? idx : 0;
}

export function resolveSenseId(
  entry: VocabEntry | null,
  senseId: string,
): string {
  if (!entry || !entry.senses || entry.senses.length === 0) return senseId;

  if (senseId === "primary") {
    return getPrimarySenseId(entry);
  }

  const exists = entry.senses.some((s) => s.sense_id === senseId);
  if (exists) return senseId;

  return getPrimarySenseId(entry);
}

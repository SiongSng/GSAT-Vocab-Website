import { type Card as FSRSCard, type ReviewLog as FSRSReviewLog, State, Rating } from "ts-fsrs";

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

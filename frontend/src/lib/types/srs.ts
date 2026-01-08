import {
  type Card as FSRSCard,
  type ReviewLog as FSRSReviewLog,
  State,
  Rating,
} from "ts-fsrs";
import type { VocabSense, WordEntry, PhraseEntry } from "./vocab";
import { sortSensesByExamFrequency } from "./vocab";

export { State, Rating };

export type SRSEntryType = "word" | "phrase";

export type SRSEligibleEntry = WordEntry | PhraseEntry;

export type SkillType = "reverse" | "fill_blank" | "spelling" | "distinction";

export interface SkillState {
  due: Date;
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  state: State;
  last_review?: Date;
}

export type SkillStates = Partial<Record<SkillType, SkillState>>;

export interface SRSCard extends FSRSCard {
  lemma: string;
  sense_id: string;
  entry_type: SRSEntryType;
  skills?: SkillStates;
}

export const SKILL_UNLOCK_THRESHOLDS: Record<SkillType, number> = {
  reverse: 1,
  fill_blank: 3,
  spelling: 7,
  distinction: 21,
};

export const SKILL_INFLUENCE_ON_MAIN: Record<SkillType, number> = {
  reverse: 0.3,
  fill_blank: 0.5,
  spelling: 0.7,
  distinction: 0.8,
};

export function getUnlockedSkills(mainStability: number): SkillType[] {
  const skills: SkillType[] = [];
  for (const [skill, threshold] of Object.entries(SKILL_UNLOCK_THRESHOLDS)) {
    if (mainStability >= threshold) {
      skills.push(skill as SkillType);
    }
  }
  return skills;
}

export function createEmptySkillState(): SkillState {
  return {
    due: new Date(),
    stability: 0,
    difficulty: 0,
    reps: 0,
    lapses: 0,
    state: State.New,
  };
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

export function getPrioritizedSenses(entry: SRSEligibleEntry): PrioritizedSense[] {
  if (!entry.senses || entry.senses.length === 0) return [];

  const sortedSenses = sortSensesByExamFrequency(entry.senses);

  return sortedSenses.map((sense, idx) => ({
    sense,
    priority: idx,
    isPrimary: idx === 0,
  }));
}

export function getPrimarySenseId(entry: SRSEligibleEntry): string {
  const prioritized = getPrioritizedSenses(entry);
  return prioritized.length > 0 ? prioritized[0].sense.sense_id : "primary";
}

export function getSensePriorityIndex(
  entry: SRSEligibleEntry,
  senseId: string,
): number {
  const prioritized = getPrioritizedSenses(entry);
  const idx = prioritized.findIndex((p) => p.sense.sense_id === senseId);
  return idx >= 0 ? idx : 0;
}

export function resolveSenseId(
  entry: SRSEligibleEntry | null,
  senseId: string,
): string {
  if (!entry || !entry.senses || entry.senses.length === 0) return senseId;

  if (senseId === "primary") {
    return getPrimarySenseId(entry);
  }

  const exists = entry.senses.some((s: VocabSense) => s.sense_id === senseId);
  if (exists) return senseId;

  return getPrimarySenseId(entry);
}

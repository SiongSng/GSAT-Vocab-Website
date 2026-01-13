import { Rating, State } from "ts-fsrs";
import type { QuizQuestionType } from "./quiz-generator";
import { quizTypeToSkillType } from "./quiz-generator";
import {
  getCard,
  ensureCard,
  updateCard,
  addReviewLog,
  updateDailyStats,
  saveNow,
} from "./srs-storage";
import type { SRSCard, SRSReviewLog, SkillState } from "$lib/types/srs";
import {
  SKILL_INFLUENCE_ON_MAIN,
  createEmptySkillState,
} from "$lib/types/srs";
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
  matched_inflected?: boolean;
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

  if (result.question_type === "spelling" && result.matched_inflected) {
    return Rating.Easy;
  }

  const isHardType = HARD_QUESTION_TYPES.includes(result.question_type);

  if (isHardType && result.response_time_ms < FAST_RESPONSE_MS) {
    return Rating.Easy;
  }

  return Rating.Good;
}

function blendRatingForMain(
  skillRating: Rating,
  influence: number,
): Rating {
  if (skillRating === Rating.Again) {
    return influence >= 0.5 ? Rating.Again : Rating.Hard;
  }
  if (skillRating === Rating.Hard) {
    return influence >= 0.7 ? Rating.Hard : Rating.Good;
  }
  if (skillRating === Rating.Easy) {
    return influence >= 0.5 ? Rating.Easy : Rating.Good;
  }
  return Rating.Good;
}

function createFSRSCompatibleCard(state: SkillState): any {
  return {
    due: new Date(state.due),
    stability: state.stability,
    difficulty: state.difficulty,
    elapsed_days: 0,
    scheduled_days: 0,
    reps: state.reps,
    lapses: state.lapses,
    state: state.state,
    last_review: state.last_review ? new Date(state.last_review) : undefined,
  };
}

function extractSkillStateFromFSRS(fsrsCard: any): SkillState {
  return {
    due: fsrsCard.due,
    stability: fsrsCard.stability,
    difficulty: fsrsCard.difficulty,
    reps: fsrsCard.reps,
    lapses: fsrsCard.lapses,
    state: fsrsCard.state,
    last_review: fsrsCard.last_review,
  };
}

export function recordQuizResult(result: QuizResult): void {
  let card = getCard(result.lemma, result.sense_id);

  if (!card) {
    card = ensureCard(result.lemma, result.sense_id, result.entry_type).card;
  }

  const rating = mapQuizResultToRating(result);
  const now = new Date();
  const wasNew = card.state === State.New;

  const skillType = quizTypeToSkillType(result.question_type);

  let updatedSkills = card.skills ? { ...card.skills } : {};
  let mainRating = rating;

  if (skillType) {
    const existingSkillState = card.skills?.[skillType];
    const skillState = existingSkillState ?? createEmptySkillState();

    const fsrsSkillCard = createFSRSCompatibleCard(skillState);
    const skillScheduling = fsrs.repeat(fsrsSkillCard, now);
    const skillRecordLog = skillScheduling[rating as Exclude<Rating, Rating.Manual>];

    if (skillRecordLog) {
      const newSkillState = extractSkillStateFromFSRS(skillRecordLog.card);
      updatedSkills[skillType] = newSkillState;
    }

    const influence = SKILL_INFLUENCE_ON_MAIN[skillType];
    mainRating = blendRatingForMain(rating, influence);
  }

  const mainScheduling = fsrs.repeat(card, now);
  const mainRecordLog = mainScheduling[mainRating as Exclude<Rating, Rating.Manual>];

  if (!mainRecordLog) return;

  const { card: newMainCard, log } = mainRecordLog;

  const updatedCard: SRSCard = {
    ...newMainCard,
    lemma: card.lemma,
    sense_id: card.sense_id,
    entry_type: card.entry_type,
    skills: updatedSkills,
  };

  updateCard(updatedCard);

  const reviewLog: SRSReviewLog = {
    ...log,
    lemma: updatedCard.lemma,
    sense_id: updatedCard.sense_id,
  };

  void addReviewLog(reviewLog).catch(() => {});
  void updateDailyStats(rating, wasNew, result.response_time_ms).catch(() => {});
}

export function applyQuizSessionResults(results: QuizResult[]): void {
  for (const result of results) {
    recordQuizResult(result);
  }

  void saveNow();
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

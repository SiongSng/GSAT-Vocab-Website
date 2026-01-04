import {
  generateQuizLocally,
  type QuizQuestion,
  type QuizConfig as GeneratorConfig,
  type QuizQuestionType,
} from "./quiz-generator";
import {
  applyQuizSessionResults,
  type QuizResult,
  computeSessionSummary,
  type QuizSessionSummary,
} from "./quiz-srs-bridge";

export type { QuizQuestion, QuizQuestionType };

interface QuizStore {
  type: QuizQuestionType | "adaptive" | null;
  source: "srs_due" | "srs_weak" | "today_studied" | "custom";
  questions: QuizQuestion[];
  currentIndex: number;
  results: QuizResult[];
  isLoading: boolean;
  isActive: boolean;
  isComplete: boolean;
  error: string | null;

  sessionStartTime: Date | null;
  questionStartTime: Date | null;
  usedHintForCurrent: boolean;
}

const store: QuizStore = $state({
  type: null,
  source: "srs_due",
  questions: [],
  currentIndex: 0,
  results: [],
  isLoading: false,
  isActive: false,
  isComplete: false,
  error: null,
  sessionStartTime: null,
  questionStartTime: null,
  usedHintForCurrent: false,
});

const currentQuestion = $derived(
  store.questions.length > 0 ? store.questions[store.currentIndex] : null
);

const score = $derived(
  store.results.filter((r) => r.correct).length
);

const progress = $derived({
  current: store.currentIndex + 1,
  total: store.questions.length,
  answered: store.results.length,
});

const incorrectQuestions = $derived(
  store.questions.filter((_, idx) => {
    const result = store.results[idx];
    return result && !result.correct;
  })
);

const sessionSummary = $derived<QuizSessionSummary | null>(
  store.isComplete ? computeSessionSummary(store.results) : null
);

export function getQuizStore() {
  return {
    get type() {
      return store.type;
    },
    get source() {
      return store.source;
    },
    get questions() {
      return store.questions;
    },
    get currentIndex() {
      return store.currentIndex;
    },
    get results() {
      return store.results;
    },
    get isLoading() {
      return store.isLoading;
    },
    get isActive() {
      return store.isActive;
    },
    get isComplete() {
      return store.isComplete;
    },
    get error() {
      return store.error;
    },
    get currentQuestion() {
      return currentQuestion;
    },
    get score() {
      return score;
    },
    get progress() {
      return progress;
    },
    get incorrectQuestions() {
      return incorrectQuestions;
    },
    get sessionSummary() {
      return sessionSummary;
    },
    get usedHintForCurrent() {
      return store.usedHintForCurrent;
    },
  };
}

export interface QuizConfig {
  source?: "srs_due" | "srs_weak" | "today_studied" | "custom";
  count: number;
  lemmas?: string[];
  entry_type?: "word" | "phrase" | "all";
  pos_filter?: string[];
  force_type?: QuizQuestionType;
}

export async function startQuiz(config: QuizConfig): Promise<void> {
  store.isLoading = true;
  store.error = null;

  try {
    const generatorConfig: GeneratorConfig = {
      source: config.source ?? "srs_due",
      count: config.count,
      lemmas: config.lemmas,
      entry_type: config.entry_type,
      pos_filter: config.pos_filter,
      force_type: config.force_type,
    };

    const questions = await generateQuizLocally(generatorConfig);

    if (questions.length === 0) {
      store.error = "沒有可用的題目。請先加入一些單字到學習清單。";
      store.isLoading = false;
      return;
    }

    store.type = config.force_type ?? "adaptive";
    store.source = config.source ?? "srs_due";
    store.questions = questions;
    store.currentIndex = 0;
    store.results = [];
    store.isActive = true;
    store.isComplete = false;
    store.sessionStartTime = new Date();
    store.questionStartTime = new Date();
    store.usedHintForCurrent = false;
  } catch (e) {
    store.error = e instanceof Error ? e.message : "生成測驗失敗";
    console.error("Failed to generate quiz:", e);
  } finally {
    store.isLoading = false;
  }
}

export function markHintUsed(): void {
  store.usedHintForCurrent = true;
}

export function submitAnswer(answer: string): void {
  if (!store.isActive || store.currentIndex >= store.questions.length) return;

  const question = store.questions[store.currentIndex];
  const responseTime = store.questionStartTime
    ? Date.now() - store.questionStartTime.getTime()
    : 0;

  const isCorrect = answer.toLowerCase() === question.correct.toLowerCase();

  const result: QuizResult = {
    lemma: question.lemma,
    sense_id: question.sense_id,
    entry_type: question.entry_type,
    question_type: question.type,
    correct: isCorrect,
    response_time_ms: responseTime,
    used_hint: store.usedHintForCurrent,
  };

  store.results[store.currentIndex] = result;
}

export function nextQuestion(): void {
  if (store.currentIndex < store.questions.length - 1) {
    store.currentIndex++;
    store.questionStartTime = new Date();
    store.usedHintForCurrent = false;
  } else {
    store.isComplete = true;
    store.isActive = false;
    applyQuizSessionResults(store.results);
  }
}

export function previousQuestion(): void {
  if (store.currentIndex > 0) {
    store.currentIndex--;
    store.questionStartTime = new Date();
    store.usedHintForCurrent = false;
  }
}

export function goToQuestion(index: number): void {
  if (index >= 0 && index < store.questions.length) {
    store.currentIndex = index;
    store.questionStartTime = new Date();
    store.usedHintForCurrent = false;
  }
}

export function resetQuiz(): void {
  store.type = null;
  store.source = "srs_due";
  store.questions = [];
  store.currentIndex = 0;
  store.results = [];
  store.isLoading = false;
  store.isActive = false;
  store.isComplete = false;
  store.error = null;
  store.sessionStartTime = null;
  store.questionStartTime = null;
  store.usedHintForCurrent = false;
}

export function exitQuiz(): void {
  if (store.results.length > 0) {
    applyQuizSessionResults(store.results);
  }
  store.isActive = false;
  store.isComplete = false;
}

export async function retryIncorrect(): Promise<void> {
  const incorrect = incorrectQuestions;
  if (incorrect.length === 0) return;

  const lemmas = incorrect.map((q) => q.lemma).filter(Boolean) as string[];
  if (lemmas.length === 0) return;

  store.isLoading = true;
  store.error = null;

  try {
    const questions = await generateQuizLocally({
      source: "custom",
      count: lemmas.length,
      lemmas,
      force_type: store.type === "adaptive" ? undefined : (store.type as QuizQuestionType),
    });

    store.questions = questions;
    store.currentIndex = 0;
    store.results = [];
    store.isActive = true;
    store.isComplete = false;
    store.sessionStartTime = new Date();
    store.questionStartTime = new Date();
    store.usedHintForCurrent = false;
  } catch (e) {
    store.error = e instanceof Error ? e.message : "重試失敗";
    console.error("Failed to retry quiz:", e);
  } finally {
    store.isLoading = false;
  }
}

export function isAnswerCorrect(index: number): boolean | null {
  const result = store.results[index];
  if (!result) return null;
  return result.correct;
}

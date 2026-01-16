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
import {
  getAllWordForms,
  getAllPhraseForms,
} from "$lib/utils/word-forms";

export type { QuizQuestion, QuizQuestionType };

interface QuizStore {
  type: QuizQuestionType | "adaptive" | null;
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
  store.questions.length > 0 ? store.questions[store.currentIndex] : null,
);

const score = $derived(store.results.filter((r) => r.correct).length);

const progress = $derived({
  current: store.currentIndex + 1,
  total: store.questions.length,
  answered: store.results.length,
});

const incorrectQuestions = $derived(
  store.questions.filter((_, idx) => {
    const result = store.results[idx];
    return result && !result.correct;
  }),
);

const sessionSummary = $derived<QuizSessionSummary | null>(
  store.isComplete ? computeSessionSummary(store.results) : null,
);

export function getQuizStore() {
  return {
    get type() {
      return store.type;
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
  count: number;
  entry_type?: "word" | "phrase" | "all";
  force_types?: QuizQuestionType[];
  levelFilter?: number[];
  officialOnly?: boolean;
}

export async function startQuiz(config: QuizConfig): Promise<void> {
  store.isLoading = true;
  store.error = null;

  try {
    const generatorConfig: GeneratorConfig = {
      count: config.count,
      entry_type: config.entry_type,
      force_types: config.force_types,
      levelFilter: config.levelFilter,
      officialOnly: config.officialOnly,
    };

    const questions = await generateQuizLocally(generatorConfig);

    if (questions.length === 0) {
      let entryTypeText = "題目";
      if (config.entry_type === "phrase") {
        entryTypeText = "片語";
      } else if (config.entry_type === "word") {
        entryTypeText = "單字";
      }
      const learnHint = config.entry_type === "phrase" ? "片語" : "單字";
      store.error = `沒有可用的${entryTypeText}。請先在 Flashcard 學習一些${learnHint}。`;
      store.isLoading = false;
      return;
    }

    store.type =
      config.force_types?.length === 1 ? config.force_types[0] : "adaptive";
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

  const answerLower = answer.toLowerCase();
  const correctLower = question.correct.toLowerCase();

  let isCorrect = answerLower === correctLower;
  let matchedInflected = false;

  if (question.type === "spelling") {
    const inflectedLower = question.inflected_form?.toLowerCase();

    if (inflectedLower && answerLower === inflectedLower) {
      isCorrect = true;
      matchedInflected = true;
    } else if (!isCorrect) {
      const validForms =
        question.entry_type === "phrase"
          ? getAllPhraseForms(question.lemma)
          : getAllWordForms(question.lemma);
      isCorrect = validForms.has(answerLower);
    }
  }

  const result: QuizResult = {
    lemma: question.lemma,
    sense_id: question.sense_id,
    entry_type: question.entry_type,
    question_type: question.type,
    correct: isCorrect,
    response_time_ms: responseTime,
    used_hint: store.usedHintForCurrent,
    matched_inflected: matchedInflected,
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

  store.isLoading = true;
  store.error = null;

  try {
    const lemmas = incorrect.map((q) => q.lemma);
    const questions = await generateQuizLocally({
      count: incorrect.length,
      force_types:
        store.type === "adaptive"
          ? undefined
          : [store.type as QuizQuestionType],
      specific_lemmas: lemmas,
    });

    if (questions.length === 0) {
      store.error = "無法重新生成題目";
      store.isLoading = false;
      return;
    }

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

export function didMatchInflected(index: number): boolean {
  const result = store.results[index];
  return result?.matched_inflected ?? false;
}

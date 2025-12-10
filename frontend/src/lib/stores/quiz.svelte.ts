import { generateQuiz, type QuizQuestion } from "$lib/api";

interface QuizStore {
  type: "choice" | "spelling" | "fill" | null;
  questions: QuizQuestion[];
  currentIndex: number;
  answers: (string | null)[];
  isLoading: boolean;
  isActive: boolean;
  isComplete: boolean;
  error: string | null;
}

const store: QuizStore = $state({
  type: null,
  questions: [],
  currentIndex: 0,
  answers: [],
  isLoading: false,
  isActive: false,
  isComplete: false,
  error: null,
});

const currentQuestion = $derived(
  store.questions.length > 0 ? store.questions[store.currentIndex] : null,
);

const score = $derived(
  store.answers.reduce((acc, answer, idx) => {
    if (answer === null) return acc;
    const q = store.questions[idx];
    return acc + (answer.toLowerCase() === q.correct.toLowerCase() ? 1 : 0);
  }, 0),
);

const progress = $derived({
  current: store.currentIndex + 1,
  total: store.questions.length,
  answered: store.answers.filter((a) => a !== null).length,
});

const incorrectQuestions = $derived(
  store.questions.filter((q, idx) => {
    const answer = store.answers[idx];
    return answer !== null && answer.toLowerCase() !== q.correct.toLowerCase();
  }),
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
    get answers() {
      return store.answers;
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
  };
}

export interface QuizConfig {
  type: "choice" | "spelling" | "fill";
  count: number;
  freqMin?: number;
  freqMax?: number;
  pos?: string[];
  excludePropn?: boolean;
  choiceDirection?: "word_to_def" | "def_to_word";
}

export async function startQuiz(config: QuizConfig): Promise<void> {
  store.isLoading = true;
  store.error = null;

  try {
    const questions = await generateQuiz({
      type: config.type,
      count: config.count,
      freqMin: config.freqMin,
      freqMax: config.freqMax,
      pos: config.pos,
      excludePropn: config.excludePropn,
      choiceDirection: config.choiceDirection,
    });

    store.type = config.type;
    store.questions = questions;
    store.currentIndex = 0;
    store.answers = new Array(questions.length).fill(null);
    store.isActive = true;
    store.isComplete = false;
  } catch (e) {
    store.error = e instanceof Error ? e.message : "Failed to generate quiz";
    console.error("Failed to generate quiz:", e);
  } finally {
    store.isLoading = false;
  }
}

export function submitAnswer(answer: string): void {
  if (!store.isActive || store.currentIndex >= store.questions.length) return;

  store.answers[store.currentIndex] = answer;
}

export function nextQuestion(): void {
  if (store.currentIndex < store.questions.length - 1) {
    store.currentIndex++;
  } else {
    store.isComplete = true;
    store.isActive = false;
  }
}

export function previousQuestion(): void {
  if (store.currentIndex > 0) {
    store.currentIndex--;
  }
}

export function goToQuestion(index: number): void {
  if (index >= 0 && index < store.questions.length) {
    store.currentIndex = index;
  }
}

export function resetQuiz(): void {
  store.type = null;
  store.questions = [];
  store.currentIndex = 0;
  store.answers = [];
  store.isLoading = false;
  store.isActive = false;
  store.isComplete = false;
  store.error = null;
}

export function exitQuiz(): void {
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
    const questions = await generateQuiz({
      type: store.type!,
      count: lemmas.length,
      lemmas,
    });

    store.questions = questions;
    store.currentIndex = 0;
    store.answers = new Array(questions.length).fill(null);
    store.isActive = true;
    store.isComplete = false;
  } catch (e) {
    store.error = e instanceof Error ? e.message : "Failed to retry quiz";
    console.error("Failed to retry quiz:", e);
  } finally {
    store.isLoading = false;
  }
}

export function isAnswerCorrect(index: number): boolean | null {
  const answer = store.answers[index];
  if (answer === null) return null;

  const q = store.questions[index];
  return answer.toLowerCase() === q.correct.toLowerCase();
}

export function getCurrentAnswer(): string | null {
  return store.answers[store.currentIndex];
}

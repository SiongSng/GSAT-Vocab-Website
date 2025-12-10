import type { VocabWord } from "$lib/types";
import { getAudioUrl } from "$lib/api";

interface FlashcardStore {
  words: VocabWord[];
  currentIndex: number;
  knownWords: Set<string>;
  reviewWords: Set<string>;
  autoSpeak: boolean;
  isSetupOpen: boolean;
  isFlipped: boolean;
  isComplete: boolean;
}

const store: FlashcardStore = $state({
  words: [],
  currentIndex: 0,
  knownWords: new Set(),
  reviewWords: new Set(),
  autoSpeak: loadAutoSpeakPreference(),
  isSetupOpen: false,
  isFlipped: false,
  isComplete: false,
});

const currentWord = $derived(
  store.words.length > 0 ? store.words[store.currentIndex] : null
);

const progress = $derived({
  current: store.currentIndex + 1,
  total: store.words.length,
  known: store.knownWords.size,
  review: store.reviewWords.size,
});

function loadAutoSpeakPreference(): boolean {
  try {
    return localStorage.getItem("gsat_vocab_auto_speak_flashcard") !== "false";
  } catch {
    return true;
  }
}

function saveAutoSpeakPreference(value: boolean): void {
  try {
    localStorage.setItem("gsat_vocab_auto_speak_flashcard", String(value));
  } catch {
    // ignore
  }
}

export function getFlashcardStore() {
  return {
    get words() {
      return store.words;
    },
    get currentIndex() {
      return store.currentIndex;
    },
    get knownWords() {
      return store.knownWords;
    },
    get reviewWords() {
      return store.reviewWords;
    },
    get autoSpeak() {
      return store.autoSpeak;
    },
    get isSetupOpen() {
      return store.isSetupOpen;
    },
    get isFlipped() {
      return store.isFlipped;
    },
    get isComplete() {
      return store.isComplete;
    },
    get currentWord() {
      return currentWord;
    },
    get progress() {
      return progress;
    },
  };
}

export function openSetup(): void {
  store.isSetupOpen = true;
  store.isComplete = false;
}

export function closeSetup(): void {
  store.isSetupOpen = false;
}

export function startFlashcards(words: VocabWord[]): void {
  store.words = shuffleArray([...words]);
  store.currentIndex = 0;
  store.knownWords = new Set();
  store.reviewWords = new Set();
  store.isFlipped = false;
  store.isComplete = false;
  store.isSetupOpen = false;

  if (store.autoSpeak && store.words.length > 0) {
    playWordAudio(store.words[0].lemma);
  }
}

export function flipCard(): void {
  store.isFlipped = !store.isFlipped;
}

export function nextCard(): void {
  if (store.currentIndex < store.words.length - 1) {
    store.currentIndex++;
    store.isFlipped = false;

    if (store.autoSpeak) {
      playWordAudio(store.words[store.currentIndex].lemma);
    }
  } else {
    store.isComplete = true;
  }
}

export function previousCard(): void {
  if (store.currentIndex > 0) {
    store.currentIndex--;
    store.isFlipped = false;

    if (store.autoSpeak) {
      playWordAudio(store.words[store.currentIndex].lemma);
    }
  }
}

export function markKnown(): void {
  const word = currentWord;
  if (word) {
    store.knownWords.add(word.lemma);
    store.reviewWords.delete(word.lemma);
    nextCard();
  }
}

export function markReview(): void {
  const word = currentWord;
  if (word) {
    store.reviewWords.add(word.lemma);
    store.knownWords.delete(word.lemma);
    nextCard();
  }
}

export function setAutoSpeak(value: boolean): void {
  store.autoSpeak = value;
  saveAutoSpeakPreference(value);
}

export function restartAll(): void {
  store.currentIndex = 0;
  store.knownWords = new Set();
  store.reviewWords = new Set();
  store.isFlipped = false;
  store.isComplete = false;
  store.words = shuffleArray([...store.words]);

  if (store.autoSpeak && store.words.length > 0) {
    playWordAudio(store.words[0].lemma);
  }
}

export function restartReviewOnly(): void {
  const reviewLemmas = store.reviewWords;
  const reviewWords = store.words.filter((w) => reviewLemmas.has(w.lemma));

  if (reviewWords.length === 0) return;

  store.words = shuffleArray(reviewWords);
  store.currentIndex = 0;
  store.knownWords = new Set();
  store.reviewWords = new Set();
  store.isFlipped = false;
  store.isComplete = false;

  if (store.autoSpeak && store.words.length > 0) {
    playWordAudio(store.words[0].lemma);
  }
}

export function exportReviewList(): void {
  const reviewWords = store.words
    .filter((w) => store.reviewWords.has(w.lemma))
    .map((w) => w.lemma);

  if (reviewWords.length === 0) return;

  const blob = new Blob([reviewWords.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "review-words.txt";
  a.click();
  URL.revokeObjectURL(url);
}

let audioPlayer: HTMLAudioElement | null = null;

function playWordAudio(lemma: string): void {
  if (!audioPlayer) {
    audioPlayer = new Audio();
  }
  audioPlayer.src = getAudioUrl(lemma);
  audioPlayer.play().catch(() => {});
}

export function playCurrentWordAudio(): void {
  const word = currentWord;
  if (word) {
    playWordAudio(word.lemma);
  }
}

function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

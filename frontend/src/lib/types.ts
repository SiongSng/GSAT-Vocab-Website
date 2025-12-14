export interface VocabWord {
  lemma: string;
  count: number;
  primary_pos: string;
  meaning_count: number;
  zh_preview?: string;
}

export interface VocabMeaning {
  pos: string;
  en_def: string;
  zh_def: string;
}

export interface VocabSentence {
  text: string;
  source?: string;
  audio_file?: string;
  variants?: string[];
}

export interface VocabDetail {
  lemma: string;
  count: number;
  meanings: VocabMeaning[];
  pos_distribution?: Record<string, number>;
  sentences?: {
    preview: VocabSentence[];
    total_count: number;
    next_offset: number;
  };
}

export interface SearchIndex {
  by_pos: Record<string, string[]>;
}

export type ViewMode = 'browse' | 'flashcard' | 'quiz';

export type PosFilter = 'all' | 'NOUN' | 'VERB' | 'ADJ' | 'ADV' | 'PROPN';

export type VocabTypeFilter = 'all' | 'word' | 'phrase' | 'pattern';

export type TierFilter = 'all' | 'tested' | 'translation' | 'phrase' | 'pattern' | 'basic';

export type SortOption =
  | 'importance_desc'
  | 'importance_asc'
  | 'count_desc'
  | 'count_asc'
  | 'year_spread_desc'
  | 'alphabetical_asc'
  | 'alphabetical_desc'
  | 'level_asc'
  | 'level_desc';

export interface Filters {
  searchTerm: string;
  freqMin: number;
  freqMax: number;
  pos: PosFilter;
  type: VocabTypeFilter;
  tier: TierFilter;
  levels: number[];
  officialOnly: boolean;
  testedOnly: boolean;
  sortBy: SortOption;
}

export interface FlashcardState {
  currentIndex: number;
  words: VocabWord[];
  knownWords: Set<string>;
  reviewWords: Set<string>;
  autoSpeak: boolean;
  isSetupOpen: boolean;
}

export type QuizType = 'choice' | 'spelling' | 'fill' | null;

export type ChoiceDirection = 'word_to_def' | 'def_to_word';

export interface QuizQuestion {
  type: QuizType;
  promptTitle?: string;
  prompt: string;
  options?: { label: string; value: string }[];
  correct: string;
  userAnswer?: string;
  isCorrect?: boolean;
  lemma?: string;
}

export interface QuizState {
  type: QuizType;
  questions: QuizQuestion[];
  currentQuestion: number;
  score: number;
  isActive: boolean;
  isComplete: boolean;
}

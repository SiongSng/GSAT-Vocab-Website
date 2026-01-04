import type {
  WordEntry,
  PhraseEntry,
  VocabSense,
  ConfusionNote,
} from "$lib/types/vocab";
import type { SRSCard } from "$lib/types/srs";
import {
  getAllWords,
  getAllPhrases,
  getWord,
  getPhrase,
} from "./vocab-db";
import { getAllCards, getDueCards, getCard } from "./srs-storage";

export type QuizQuestionType =
  | "recognition"
  | "reverse"
  | "fill_blank"
  | "spelling"
  | "distinction";

export interface QuizQuestion {
  type: QuizQuestionType;
  lemma: string;
  sense_id: string;
  entry_type: "word" | "phrase";

  prompt: string;
  sentence_context?: string;
  hint?: string;

  options?: {
    label: string;
    value: string;
    is_from_confusion_notes?: boolean;
  }[];

  correct: string;
  accept_variants?: string[];

  exam_source?: {
    year: number;
    exam_type: string;
    section_type: string;
  };

  explanation?: {
    confusion_note?: ConfusionNote;
    memory_tip?: string;
    correct_usage: string;
  };
}

export interface QuizConfig {
  source: "srs_due" | "srs_weak" | "today_studied" | "custom";
  count: number;

  lemmas?: string[];

  entry_type?: "word" | "phrase" | "all";
  pos_filter?: string[];
  level_range?: { min: number; max: number };

  force_type?: QuizQuestionType;
}

type VocabEntry = WordEntry | PhraseEntry;

function isWordEntry(entry: VocabEntry): entry is WordEntry {
  return "pos" in entry && Array.isArray(entry.pos);
}

export function getQuizTypeForCard(card: SRSCard): QuizQuestionType {
  const stability = card.stability;
  const lapses = card.lapses;

  if (lapses >= 3 || stability < 1) {
    return "recognition";
  }
  if (stability >= 1 && stability < 3) {
    return "reverse";
  }
  if (stability >= 3 && stability < 7) {
    return "fill_blank";
  }
  if (stability >= 7 && stability < 21) {
    return "spelling";
  }
  return "distinction";
}

async function getQuizEligibleEntries(
  config: QuizConfig
): Promise<{ entry: VocabEntry; card: SRSCard }[]> {
  const results: { entry: VocabEntry; card: SRSCard }[] = [];

  // Custom source: get cards for specific lemmas
  if (config.source === "custom" && config.lemmas && config.lemmas.length > 0) {
    for (const lemma of config.lemmas) {
      const word = await getWord(lemma);
      if (word && word.senses[0]) {
        const card = getCard(lemma, word.senses[0].sense_id);
        if (card) {
          results.push({ entry: word, card });
          continue;
        }
      }
      const phrase = await getPhrase(lemma);
      if (phrase && phrase.senses[0]) {
        const card = getCard(lemma, phrase.senses[0].sense_id);
        if (card) {
          results.push({ entry: phrase, card });
        }
      }
    }
    return results;
  }

  // SRS due cards: words that need review
  if (config.source === "srs_due") {
    const dueCards = getDueCards();
    for (const card of dueCards) {
      if (config.entry_type && config.entry_type !== "all") {
        if (card.entry_type !== config.entry_type) continue;
      }
      const entry =
        card.entry_type === "phrase"
          ? await getPhrase(card.lemma)
          : await getWord(card.lemma);
      if (entry) {
        results.push({ entry, card });
      }
    }
    return results;
  }

  // SRS weak cards: words with high lapses or low stability
  if (config.source === "srs_weak") {
    const allCards = getAllCards();
    const weakCards = allCards.filter(
      (c) => c.lapses >= 2 || c.stability < 3
    );
    for (const card of weakCards) {
      if (config.entry_type && config.entry_type !== "all") {
        if (card.entry_type !== config.entry_type) continue;
      }
      const entry =
        card.entry_type === "phrase"
          ? await getPhrase(card.lemma)
          : await getWord(card.lemma);
      if (entry) {
        results.push({ entry, card });
      }
    }
    return results;
  }

  // Today studied: cards reviewed today
  if (config.source === "today_studied") {
    const allCards = getAllCards();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todayCards = allCards.filter((c) => {
      if (!c.last_review) return false;
      const reviewDate = new Date(c.last_review);
      reviewDate.setHours(0, 0, 0, 0);
      return reviewDate.getTime() === today.getTime();
    });
    
    for (const card of todayCards) {
      if (config.entry_type && config.entry_type !== "all") {
        if (card.entry_type !== config.entry_type) continue;
      }
      const entry =
        card.entry_type === "phrase"
          ? await getPhrase(card.lemma)
          : await getWord(card.lemma);
      if (entry) {
        results.push({ entry, card });
      }
    }
    return results;
  }

  // Default: return empty array (quiz should only use SRS cards)
  return results;
}

let allWordsCache: WordEntry[] | null = null;
let allPhrasesCache: PhraseEntry[] | null = null;

async function ensureDistractorPool(): Promise<{
  words: WordEntry[];
  phrases: PhraseEntry[];
}> {
  if (!allWordsCache) {
    allWordsCache = await getAllWords();
  }
  if (!allPhrasesCache) {
    allPhrasesCache = await getAllPhrases();
  }
  return { words: allWordsCache, phrases: allPhrasesCache };
}

export function clearDistractorCache(): void {
  allWordsCache = null;
  allPhrasesCache = null;
}

async function generateDistractors(
  entry: VocabEntry,
  sense: VocabSense,
  count: number,
  type: "definition" | "word"
): Promise<string[]> {
  const distractors: string[] = [];
  const usedValues = new Set<string>();

  if (type === "definition") {
    usedValues.add(sense.zh_def.toLowerCase());
  } else {
    usedValues.add(entry.lemma.toLowerCase());
  }

  if (entry.confusion_notes && entry.confusion_notes.length > 0) {
    for (const note of entry.confusion_notes) {
      if (distractors.length >= count) break;
      if (type === "word") {
        const confusedWord = note.confused_with;
        if (!usedValues.has(confusedWord.toLowerCase())) {
          distractors.push(confusedWord);
          usedValues.add(confusedWord.toLowerCase());
        }
      }
    }
  }

  if (type === "definition" && entry.senses.length > 1) {
    for (const otherSense of entry.senses) {
      if (distractors.length >= count) break;
      if (otherSense.sense_id !== sense.sense_id) {
        if (!usedValues.has(otherSense.zh_def.toLowerCase())) {
          distractors.push(otherSense.zh_def);
          usedValues.add(otherSense.zh_def.toLowerCase());
        }
      }
    }
  }

  if (distractors.length < count) {
    const pool = await ensureDistractorPool();
    const isWord = isWordEntry(entry);
    const candidates = isWord ? pool.words : pool.phrases;

    const shuffled = [...candidates].sort(() => Math.random() - 0.5);

    for (const candidate of shuffled) {
      if (distractors.length >= count) break;
      if (candidate.lemma === entry.lemma) continue;
      if (!candidate.senses || candidate.senses.length === 0) continue;

      const candidateSense = candidate.senses[0];
      if (type === "definition") {
        if (!usedValues.has(candidateSense.zh_def.toLowerCase())) {
          distractors.push(candidateSense.zh_def);
          usedValues.add(candidateSense.zh_def.toLowerCase());
        }
      } else {
        if (!usedValues.has(candidate.lemma.toLowerCase())) {
          distractors.push(candidate.lemma);
          usedValues.add(candidate.lemma.toLowerCase());
        }
      }
    }
  }

  return distractors.slice(0, count);
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function blankOutLemma(text: string, lemma: string): string {
  const lemmaPattern = new RegExp(
    `\\b${escapeRegex(lemma)}(s|es|ed|ing|er|est|ies|ied|'s|')?\\b`,
    "gi"
  );
  return text.replace(lemmaPattern, "_______");
}

function generateRecognitionQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorDefs: string[]
): QuizQuestion {
  const options = [
    { label: sense.zh_def, value: sense.zh_def },
    ...distractorDefs.map((d) => ({ label: d, value: d })),
  ].sort(() => Math.random() - 0.5);

  return {
    type: "recognition",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isWordEntry(entry) ? "word" : "phrase",
    prompt: entry.lemma,
    options,
    correct: sense.zh_def,
    hint: sense.pos ? `(${sense.pos})` : undefined,
    explanation: {
      correct_usage: sense.generated_example || sense.en_def,
    },
  };
}

function generateReverseQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorWords: string[]
): QuizQuestion {
  const options = [
    { label: entry.lemma, value: entry.lemma },
    ...distractorWords.map((d) => ({ label: d, value: d })),
  ].sort(() => Math.random() - 0.5);

  return {
    type: "reverse",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isWordEntry(entry) ? "word" : "phrase",
    prompt: sense.zh_def,
    options,
    correct: entry.lemma,
    hint: sense.pos ? `(${sense.pos})` : undefined,
    explanation: {
      correct_usage: sense.generated_example || sense.en_def,
    },
  };
}

function generateFillBlankQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorWords: string[]
): QuizQuestion {
  const example =
    sense.examples && sense.examples.length > 0
      ? sense.examples[0]
      : null;

  const sentenceText = example?.text || sense.generated_example || "";
  const blankedText = blankOutLemma(sentenceText, entry.lemma);

  const options = [
    { label: entry.lemma, value: entry.lemma },
    ...distractorWords.map((d) => ({ label: d, value: d })),
  ].sort(() => Math.random() - 0.5);

  return {
    type: "fill_blank",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isWordEntry(entry) ? "word" : "phrase",
    prompt: "填入適當的單字",
    sentence_context: blankedText,
    hint: `(${sense.pos ?? "?"}) ${sense.zh_def}`,
    options,
    correct: entry.lemma,
    exam_source: example?.source
      ? {
          year: example.source.year,
          exam_type: example.source.exam_type,
          section_type: example.source.section_type,
        }
      : undefined,
    explanation: {
      correct_usage: sentenceText,
    },
  };
}

function generateSpellingQuestion(
  entry: VocabEntry,
  sense: VocabSense
): QuizQuestion {
  return {
    type: "spelling",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isWordEntry(entry) ? "word" : "phrase",
    prompt: sense.zh_def,
    hint: sense.pos ? `(${sense.pos})` : undefined,
    correct: entry.lemma,
    accept_variants: entry.derived_forms ?? undefined,
    explanation: {
      correct_usage: sense.generated_example || sense.en_def,
    },
  };
}

function generateDistinctionQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorWords: string[]
): QuizQuestion {
  const confusionNote =
    entry.confusion_notes && entry.confusion_notes.length > 0
      ? entry.confusion_notes[0]
      : null;

  const example =
    sense.examples && sense.examples.length > 0
      ? sense.examples[0]
      : null;

  const sentenceText = example?.text || sense.generated_example || "";
  const blankedText = blankOutLemma(sentenceText, entry.lemma);

  const options = [
    { label: entry.lemma, value: entry.lemma },
    ...distractorWords.map((d, i) => ({
      label: d,
      value: d,
      is_from_confusion_notes: i === 0 && confusionNote?.confused_with === d,
    })),
  ].sort(() => Math.random() - 0.5);

  return {
    type: "distinction",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isWordEntry(entry) ? "word" : "phrase",
    prompt: "選出最適合的字",
    sentence_context: blankedText,
    hint: confusionNote?.distinction,
    options,
    correct: entry.lemma,
    exam_source: example?.source
      ? {
          year: example.source.year,
          exam_type: example.source.exam_type,
          section_type: example.source.section_type,
        }
      : undefined,
    explanation: confusionNote
      ? {
          confusion_note: confusionNote,
          memory_tip: confusionNote.memory_tip,
          correct_usage: sentenceText,
        }
      : {
          correct_usage: sentenceText,
        },
  };
}

async function generateQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  type: QuizQuestionType
): Promise<QuizQuestion> {
  switch (type) {
    case "recognition": {
      const defs = await generateDistractors(entry, sense, 3, "definition");
      return generateRecognitionQuestion(entry, sense, defs);
    }
    case "reverse": {
      const words = await generateDistractors(entry, sense, 3, "word");
      return generateReverseQuestion(entry, sense, words);
    }
    case "fill_blank": {
      const words = await generateDistractors(entry, sense, 3, "word");
      return generateFillBlankQuestion(entry, sense, words);
    }
    case "spelling":
      return generateSpellingQuestion(entry, sense);
    case "distinction": {
      const words = await generateDistractors(entry, sense, 3, "word");
      return generateDistinctionQuestion(entry, sense, words);
    }
    default:
      return generateRecognitionQuestion(
        entry,
        sense,
        await generateDistractors(entry, sense, 3, "definition")
      );
  }
}

function shuffleArray<T>(array: T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export async function generateQuizLocally(
  config: QuizConfig
): Promise<QuizQuestion[]> {
  const eligibleEntries = await getQuizEligibleEntries(config);

  if (eligibleEntries.length === 0) {
    return [];
  }

  const shuffled = shuffleArray(eligibleEntries);
  const selected = shuffled.slice(0, config.count);

  const questions: QuizQuestion[] = [];

  for (const { entry, card } of selected) {
    if (!entry.senses || entry.senses.length === 0) continue;

    const sense = entry.senses[0];
    // Use adaptive quiz type based on SRS card state, unless force_type is specified
    const quizType = config.force_type ?? getQuizTypeForCard(card);

    const question = await generateQuestion(entry, sense, quizType);
    questions.push(question);
  }

  return questions;
}

export async function getDueCount(): Promise<number> {
  const dueCards = getDueCards();
  return dueCards.length;
}

export async function getWeakCount(): Promise<number> {
  const allCards = getAllCards();
  return allCards.filter((c) => c.lapses >= 2 || c.stability < 3).length;
}

export async function getAvailableCount(): Promise<number> {
  const allCards = getAllCards();
  return allCards.length;
}

export async function getTodayStudiedCount(): Promise<number> {
  const allCards = getAllCards();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  return allCards.filter((c) => {
    if (!c.last_review) return false;
    const reviewDate = new Date(c.last_review);
    reviewDate.setHours(0, 0, 0, 0);
    return reviewDate.getTime() === today.getTime();
  }).length;
}

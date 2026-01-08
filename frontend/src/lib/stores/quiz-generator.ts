import type {
  WordEntry,
  PhraseEntry,
  VocabSense,
  ConfusionNote,
  VocabEntry,
} from "$lib/types/vocab";
import { isWordEntry } from "$lib/types/vocab";
import type { SRSCard, SkillType, SkillState } from "$lib/types/srs";
import { State } from "$lib/types/srs";
import { getAllWords, getAllPhrases, getWord, getPhrase } from "./vocab-db";
import {
  getAllCards,
  getNewSkillsForCard,
} from "./srs-storage";
import {
  getAllWordForms,
  getAllPhraseForms,
} from "$lib/utils/word-forms";

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
  inflected_form?: string;
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
  count: number;
  entry_type?: "word" | "phrase" | "all";
  force_type?: QuizQuestionType;
  specific_lemmas?: string[];
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

export function skillTypeToQuizType(skillType: SkillType): QuizQuestionType {
  return skillType as QuizQuestionType;
}

export function quizTypeToSkillType(quizType: QuizQuestionType): SkillType | null {
  if (quizType === "recognition") return null;
  return quizType as SkillType;
}

function isLearned(card: SRSCard): boolean {
  return card.state !== State.New;
}

interface QuizEligibleEntry {
  entry: VocabEntry;
  card: SRSCard;
  skillType: SkillType | null;
  skillState: SkillState | null;
  priority: "due_skill" | "new_skill" | "due_main" | "weak" | "other";
}

async function getQuizEligibleEntries(
  config: QuizConfig,
): Promise<QuizEligibleEntry[]> {
  const allCards = getAllCards();
  if (allCards.length === 0) return [];

  const now = new Date();
  const dueSkillEntries: QuizEligibleEntry[] = [];
  const newSkillEntries: QuizEligibleEntry[] = [];
  const dueMainEntries: QuizEligibleEntry[] = [];
  const weakEntries: QuizEligibleEntry[] = [];

  const seenKeys = new Set<string>();

  for (const card of allCards) {
    if (!isLearned(card)) continue;

    if (config.entry_type && config.entry_type !== "all") {
      if (card.entry_type !== config.entry_type) continue;
    }

    if (config.specific_lemmas && config.specific_lemmas.length > 0) {
      if (!config.specific_lemmas.includes(card.lemma)) continue;
    }

    const entry =
      card.entry_type === "phrase"
        ? await getPhrase(card.lemma)
        : await getWord(card.lemma);
    if (!entry) continue;

    if (card.skills) {
      for (const [skill, state] of Object.entries(card.skills)) {
        if (!state) continue;
        const skillType = skill as SkillType;
        const key = `${card.lemma}::${card.sense_id}::${skillType}`;
        if (seenKeys.has(key)) continue;

        if (new Date(state.due) <= now) {
          seenKeys.add(key);
          dueSkillEntries.push({
            entry,
            card,
            skillType,
            skillState: state,
            priority: "due_skill",
          });
        }
      }
    }

    const newSkills = getNewSkillsForCard(card);
    for (const skillType of newSkills) {
      const key = `${card.lemma}::${card.sense_id}::${skillType}`;
      if (seenKeys.has(key)) continue;
      seenKeys.add(key);

      newSkillEntries.push({
        entry,
        card,
        skillType,
        skillState: null,
        priority: "new_skill",
      });
    }

    const mainKey = `${card.lemma}::${card.sense_id}::main`;
    if (!seenKeys.has(mainKey)) {
      const isDue = new Date(card.due) <= now;
      const isWeak = card.lapses >= 2 || card.stability < 3;

      if (isDue) {
        seenKeys.add(mainKey);
        dueMainEntries.push({
          entry,
          card,
          skillType: null,
          skillState: null,
          priority: "due_main",
        });
      } else if (isWeak) {
        seenKeys.add(mainKey);
        weakEntries.push({
          entry,
          card,
          skillType: null,
          skillState: null,
          priority: "weak",
        });
      }
    }
  }

  return [
    ...dueSkillEntries,
    ...newSkillEntries,
    ...dueMainEntries,
    ...weakEntries,
  ];
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

function getExcludedLemmas(entry: VocabEntry): Set<string> {
  const excluded = new Set<string>();
  excluded.add(entry.lemma.toLowerCase());

  if (entry.synonyms) {
    for (const syn of entry.synonyms) {
      excluded.add(syn.toLowerCase());
    }
  }

  if (entry.derived_forms) {
    for (const form of entry.derived_forms) {
      excluded.add(form.toLowerCase());
    }
  }

  return excluded;
}

function getEntryPOS(entry: VocabEntry): string | null {
  if (isWordEntry(entry)) {
    return entry.pos?.[0] ?? null;
  }
  return null;
}

function getEntryLevel(entry: VocabEntry): number | null {
  if (isWordEntry(entry)) {
    return entry.level;
  }
  return null;
}

async function generateDistractors(
  entry: VocabEntry,
  sense: VocabSense,
  count: number,
  type: "definition" | "word",
): Promise<string[]> {
  const distractors: string[] = [];
  const usedValues = new Set<string>();
  const excludedLemmas = getExcludedLemmas(entry);

  if (type === "definition") {
    usedValues.add(sense.zh_def.toLowerCase());
  } else {
    usedValues.add(entry.lemma.toLowerCase());
  }

  const pool = await ensureDistractorPool();
  const entryIsWord = isWordEntry(entry);
  const candidates = entryIsWord ? pool.words : pool.phrases;
  const entryPOS = getEntryPOS(entry);
  const entryLevel = getEntryLevel(entry);

  if (
    type === "word" &&
    entry.confusion_notes &&
    entry.confusion_notes.length > 0
  ) {
    for (const note of entry.confusion_notes) {
      if (distractors.length >= count) break;
      const confusedWord = note.confused_with.toLowerCase();
      if (!usedValues.has(confusedWord) && !excludedLemmas.has(confusedWord)) {
        distractors.push(note.confused_with);
        usedValues.add(confusedWord);
      }
    }
  }

  if (
    distractors.length < count &&
    entryIsWord &&
    entryPOS &&
    entryLevel !== null
  ) {
    const samePOSAndLevel = candidates.filter((c) => {
      if (c.lemma === entry.lemma) return false;
      if (excludedLemmas.has(c.lemma.toLowerCase())) return false;
      if (!c.senses || c.senses.length === 0) return false;
      if (!isWordEntry(c)) return false;
      return c.pos?.[0] === entryPOS && c.level === entryLevel;
    });

    const shuffled = [...samePOSAndLevel].sort(() => Math.random() - 0.5);
    for (const candidate of shuffled) {
      if (distractors.length >= count) break;
      const candidateSense = candidate.senses[0];
      if (type === "definition") {
        const defLower = candidateSense.zh_def.toLowerCase();
        if (!usedValues.has(defLower)) {
          distractors.push(candidateSense.zh_def);
          usedValues.add(defLower);
        }
      } else {
        const lemmaLower = candidate.lemma.toLowerCase();
        if (!usedValues.has(lemmaLower)) {
          distractors.push(candidate.lemma);
          usedValues.add(lemmaLower);
        }
      }
    }
  }

  if (distractors.length < count && entryIsWord && entryPOS) {
    const samePOS = candidates.filter((c) => {
      if (c.lemma === entry.lemma) return false;
      if (excludedLemmas.has(c.lemma.toLowerCase())) return false;
      if (!c.senses || c.senses.length === 0) return false;
      if (!isWordEntry(c)) return false;
      return c.pos?.[0] === entryPOS;
    });

    const shuffled = [...samePOS].sort(() => Math.random() - 0.5);
    for (const candidate of shuffled) {
      if (distractors.length >= count) break;
      const candidateSense = candidate.senses[0];
      if (type === "definition") {
        const defLower = candidateSense.zh_def.toLowerCase();
        if (!usedValues.has(defLower)) {
          distractors.push(candidateSense.zh_def);
          usedValues.add(defLower);
        }
      } else {
        const lemmaLower = candidate.lemma.toLowerCase();
        if (!usedValues.has(lemmaLower)) {
          distractors.push(candidate.lemma);
          usedValues.add(lemmaLower);
        }
      }
    }
  }

  if (distractors.length < count) {
    const shuffled = [...candidates].sort(() => Math.random() - 0.5);

    for (const candidate of shuffled) {
      if (distractors.length >= count) break;
      if (candidate.lemma === entry.lemma) continue;
      if (excludedLemmas.has(candidate.lemma.toLowerCase())) continue;
      if (!candidate.senses || candidate.senses.length === 0) continue;

      const candidateSense = candidate.senses[0];
      if (type === "definition") {
        const defLower = candidateSense.zh_def.toLowerCase();
        if (!usedValues.has(defLower)) {
          distractors.push(candidateSense.zh_def);
          usedValues.add(defLower);
        }
      } else {
        const lemmaLower = candidate.lemma.toLowerCase();
        if (!usedValues.has(lemmaLower)) {
          distractors.push(candidate.lemma);
          usedValues.add(lemmaLower);
        }
      }
    }
  }

  return distractors.slice(0, count);
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractInflectedForm(
  text: string,
  lemma: string,
  isPhrase: boolean,
): string | null {
  const forms = isPhrase ? getAllPhraseForms(lemma) : getAllWordForms(lemma);
  const escapedForms = Array.from(forms).map(escapeRegex);
  const pattern = new RegExp(`\\b(${escapedForms.join("|")})\\b`, "gi");
  const match = pattern.exec(text);
  return match ? match[1] : null;
}

function blankOutLemma(
  text: string,
  lemma: string,
  isPhrase: boolean,
): string {
  const forms = isPhrase ? getAllPhraseForms(lemma) : getAllWordForms(lemma);
  const escapedForms = Array.from(forms).map(escapeRegex);
  const pattern = new RegExp(`\\b(${escapedForms.join("|")})\\b`, "gi");
  return text.replace(pattern, "_______");
}

function generateRecognitionQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorDefs: string[],
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
  distractorWords: string[],
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
  distractorWords: string[],
): QuizQuestion {
  const example =
    sense.examples && sense.examples.length > 0 ? sense.examples[0] : null;
  const isPhrase = !isWordEntry(entry);

  const sentenceText = example?.text || sense.generated_example || "";
  const blankedText = blankOutLemma(sentenceText, entry.lemma, isPhrase);

  const options = [
    { label: entry.lemma, value: entry.lemma },
    ...distractorWords.map((d) => ({ label: d, value: d })),
  ].sort(() => Math.random() - 0.5);

  return {
    type: "fill_blank",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isPhrase ? "phrase" : "word",
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
  sense: VocabSense,
): QuizQuestion {
  const example =
    sense.examples && sense.examples.length > 0 ? sense.examples[0] : null;
  const isPhrase = !isWordEntry(entry);

  const sentenceText = example?.text || sense.generated_example || "";
  const inflectedForm = sentenceText
    ? extractInflectedForm(sentenceText, entry.lemma, isPhrase)
    : null;
  const blankedText = sentenceText
    ? blankOutLemma(sentenceText, entry.lemma, isPhrase)
    : undefined;

  return {
    type: "spelling",
    lemma: entry.lemma,
    sense_id: sense.sense_id,
    entry_type: isPhrase ? "phrase" : "word",
    prompt: sense.zh_def,
    sentence_context: blankedText,
    hint: sense.pos ? `(${sense.pos})` : undefined,
    correct: entry.lemma,
    inflected_form: inflectedForm ?? undefined,
    accept_variants: entry.derived_forms ?? undefined,
    exam_source: example?.source
      ? {
          year: example.source.year,
          exam_type: example.source.exam_type,
          section_type: example.source.section_type,
        }
      : undefined,
    explanation: {
      correct_usage: sentenceText || sense.en_def,
    },
  };
}

function generateDistinctionQuestion(
  entry: VocabEntry,
  sense: VocabSense,
  distractorWords: string[],
): QuizQuestion {
  const confusionNote =
    entry.confusion_notes && entry.confusion_notes.length > 0
      ? entry.confusion_notes[0]
      : null;

  const example =
    sense.examples && sense.examples.length > 0 ? sense.examples[0] : null;
  const isPhrase = !isWordEntry(entry);

  const sentenceText = example?.text || sense.generated_example || "";
  const blankedText = blankOutLemma(sentenceText, entry.lemma, isPhrase);

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
    entry_type: isPhrase ? "phrase" : "word",
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
  type: QuizQuestionType,
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
        await generateDistractors(entry, sense, 3, "definition"),
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
  config: QuizConfig,
): Promise<QuizQuestion[]> {
  const eligibleEntries = await getQuizEligibleEntries(config);

  if (eligibleEntries.length === 0) {
    return [];
  }

  const selected: QuizEligibleEntry[] = [];
  const seenLemmas = new Set<string>();

  for (const entry of eligibleEntries) {
    if (selected.length >= config.count) break;
    if (seenLemmas.has(entry.card.lemma)) continue;

    seenLemmas.add(entry.card.lemma);
    selected.push(entry);
  }

  const shuffledSelected = shuffleArray(selected);

  const questions: QuizQuestion[] = [];

  for (const { entry, card, skillType } of shuffledSelected) {
    if (!entry.senses || entry.senses.length === 0) continue;

    const sense = entry.senses[0];

    let quizType: QuizQuestionType;
    if (config.force_type) {
      quizType = config.force_type;
    } else if (skillType) {
      quizType = skillTypeToQuizType(skillType);
    } else {
      quizType = getQuizTypeForCard(card);
    }

    const question = await generateQuestion(entry, sense, quizType);
    question.sense_id = card.sense_id;
    questions.push(question);
  }

  return questions;
}

export function getAvailableCount(): number {
  const allCards = getAllCards();
  return allCards.filter(isLearned).length;
}

export function getQuizStats() {
  const allCards = getAllCards();
  const now = new Date();

  const learnedCards = allCards.filter(isLearned);
  const dueCards = learnedCards.filter((c) => new Date(c.due) <= now);
  const weakCards = learnedCards.filter(
    (c) => c.lapses >= 2 || c.stability < 3,
  );

  const reviewSet = new Set([...dueCards, ...weakCards]);
  const reviewCards = Array.from(reviewSet);

  let dueSkillCount = 0;
  let newSkillCount = 0;
  for (const card of learnedCards) {
    if (card.skills) {
      for (const [, state] of Object.entries(card.skills)) {
        if (state && new Date(state.due) <= now) {
          dueSkillCount++;
        }
      }
    }
    const newSkills = getNewSkillsForCard(card);
    newSkillCount += newSkills.length;
  }

  const typeDistribution: Record<QuizQuestionType, number> = {
    recognition: 0,
    reverse: 0,
    fill_blank: 0,
    spelling: 0,
    distinction: 0,
  };

  for (const card of learnedCards) {
    const type = getQuizTypeForCard(card);
    typeDistribution[type]++;
  }

  return {
    total: learnedCards.length,
    due: dueCards.length,
    weak: weakCards.length,
    reviewCount: reviewCards.length,
    dueSkillCount,
    newSkillCount,
    breakdown: {
      words: reviewCards.filter((c) => c.entry_type === "word").length,
      phrases: reviewCards.filter((c) => c.entry_type === "phrase").length,
    },
    typeDistribution,
  };
}

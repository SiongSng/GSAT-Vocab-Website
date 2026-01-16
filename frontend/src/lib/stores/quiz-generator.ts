import type {
  WordEntry,
  PhraseEntry,
  VocabSense,
  ConfusionNote,
  VocabEntry,
  ExamExample,
} from "$lib/types/vocab";
import { isWordEntry } from "$lib/types/vocab";
import type { SRSCard, SkillType, SkillState } from "$lib/types/srs";
import { State, SKILL_UNLOCK_MIN_REPS } from "$lib/types/srs";
import { getAllWords, getAllPhrases, getWord, getPhrase } from "./vocab-db";
import {
  getAllCards,
  getNewSkillsForCard,
} from "./srs-storage";
import {
  getAllPhraseForms,
  getBaseForms,
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
  force_types?: QuizQuestionType[];
  specific_lemmas?: string[];
  levelFilter?: number[];
  officialOnly?: boolean;
}

/**
 * Determines the quiz question type for a card based on SRS state.
 * 
 * The function considers multiple factors:
 * - stability: Memory stability from FSRS algorithm
 * - lapses: Number of times the card was forgotten
 * - reps: Total number of reviews
 * - state: Current learning state (New, Learning, Review, Relearning)
 * 
 * This prevents generating advanced question types (like spelling) for cards
 * that were just learned, even if user pressed "Easy" on first review.
 */
export function getQuizTypeForCard(card: SRSCard): QuizQuestionType {
  const stability = card.stability;
  const lapses = card.lapses;
  const reps = card.reps;
  const state = card.state;

  // Cards with high lapses or very low stability should use recognition
  if (lapses >= 3 || stability < 1) {
    return "recognition";
  }

  // Cards still in Learning or Relearning state should use simpler question types
  if (state === State.Learning || state === State.Relearning) {
    if (stability < 3) {
      return "recognition";
    }
    return "reverse";
  }

  // For Review state cards, also consider reps to ensure sufficient exposure
  // Use the same minimum reps thresholds as skill unlock
  const MIN_REPS_FOR_REVERSE = SKILL_UNLOCK_MIN_REPS.reverse;
  const MIN_REPS_FOR_FILL_BLANK = SKILL_UNLOCK_MIN_REPS.fill_blank;
  const MIN_REPS_FOR_SPELLING = SKILL_UNLOCK_MIN_REPS.spelling;
  const MIN_REPS_FOR_DISTINCTION = SKILL_UNLOCK_MIN_REPS.distinction;

  if (stability >= 1 && stability < 3) {
    if (reps >= MIN_REPS_FOR_REVERSE) {
      return "reverse";
    }
    return "recognition";
  }
  if (stability >= 3 && stability < 7) {
    if (reps >= MIN_REPS_FOR_FILL_BLANK) {
      return "fill_blank";
    }
    if (reps >= MIN_REPS_FOR_REVERSE) {
      return "reverse";
    }
    return "recognition";
  }
  if (stability >= 7 && stability < 21) {
    if (reps >= MIN_REPS_FOR_SPELLING) {
      return "spelling";
    }
    if (reps >= MIN_REPS_FOR_FILL_BLANK) {
      return "fill_blank";
    }
    if (reps >= MIN_REPS_FOR_REVERSE) {
      return "reverse";
    }
    return "recognition";
  }
  
  // stability >= 21 (distinction level)
  if (reps >= MIN_REPS_FOR_DISTINCTION) {
    return "distinction";
  }
  if (reps >= MIN_REPS_FOR_SPELLING) {
    return "spelling";
  }
  if (reps >= MIN_REPS_FOR_FILL_BLANK) {
    return "fill_blank";
  }
  if (reps >= MIN_REPS_FOR_REVERSE) {
    return "reverse";
  }
  return "recognition";
}

export function skillTypeToQuizType(skillType: SkillType): QuizQuestionType {
  return skillType as QuizQuestionType;
}

export function quizTypeToSkillType(quizType: QuizQuestionType): SkillType | null {
  if (quizType === "recognition") return null;
  return quizType as SkillType;
}

function shuffleArray<T>(array: T[]): T[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function yieldToMain(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function isLearned(card: SRSCard): boolean {
  return card.state !== State.New;
}

interface ExampleScoringContext {
  quizType: QuizQuestionType;
}

function scoreExample(
  example: ExamExample,
  context: ExampleScoringContext,
): number {
  let score = 0;
  const source = example.source;

  const roleScores: Record<string, Record<QuizQuestionType, number>> = {
    correct_answer: {
      recognition: 10,
      reverse: 10,
      fill_blank: 15,
      spelling: 15,
      distinction: 20,
    },
    notable_phrase: {
      recognition: 5,
      reverse: 5,
      fill_blank: 8,
      spelling: 5,
      distinction: 5,
    },
    notable_pattern: {
      recognition: 4,
      reverse: 4,
      fill_blank: 6,
      spelling: 4,
      distinction: 4,
    },
    distractor: {
      recognition: 3,
      reverse: 3,
      fill_blank: 5,
      spelling: 3,
      distinction: 10,
    },
  };
  score += roleScores[source.role ?? ""]?.[context.quizType] ?? 1;

  if (context.quizType === "fill_blank" || context.quizType === "spelling") {
    if (source.sentence_role === "cloze") score += 10;
    else if (source.sentence_role === "option") score += 5;
  }

  if (source.exam_type === "gsat" || source.exam_type === "ast") score += 5;
  else if (source.exam_type === "gsat_ref") score += 2;

  const currentYear = new Date().getFullYear() - 1911;
  const yearDiff = currentYear - source.year;
  score += Math.max(0, 5 - yearDiff);

  return score;
}

function selectBestExample(
  examples: ExamExample[],
  context: ExampleScoringContext,
): ExamExample | null {
  if (!examples?.length) return null;
  if (examples.length === 1) return examples[0];

  const scored = examples.map((ex) => ({
    example: ex,
    score: scoreExample(ex, context),
  }));
  scored.sort((a, b) => b.score - a.score);

  const topScore = scored[0].score;
  const THRESHOLD_RATIO = 0.7;
  const eligibleCandidates = scored.filter(
    (s) => s.score >= topScore * THRESHOLD_RATIO,
  );

  return eligibleCandidates[
    Math.floor(Math.random() * eligibleCandidates.length)
  ].example;
}

// TODO: Remove this function after backend fixes confusion_notes generation
// Backend sometimes generates "word1 (pos) vs. word2 (pos)" format, needs frontend parsing
function parseConfusedWith(confusedWith: string): string | null {
  const trimmed = confusedWith.trim();

  const vsMatch = trimmed.match(/\bvs\.?\s+(\w+)/i);
  if (vsMatch) {
    return vsMatch[1].toLowerCase();
  }

  const posMatch = trimmed.match(/^(\w+)\s*\(/);
  if (posMatch) {
    return posMatch[1].toLowerCase();
  }

  if (/^[a-zA-Z-]+$/.test(trimmed)) {
    return trimmed.toLowerCase();
  }

  // TODO: Log unparseable formats to help backend improvement
  console.warn(
    `[confusion_notes] Cannot parse confused_with: "${confusedWith}"`,
  );
  return null;
}

function getValidConfusionNotes(
  confusionNotes: ConfusionNote[] | undefined,
  currentLemma: string,
): ConfusionNote[] {
  if (!confusionNotes?.length) return [];

  return confusionNotes
    .map((note) => {
      const parsed = parseConfusedWith(note.confused_with);
      // TODO: Backend should ensure confused_with is never the same as the original word
      if (!parsed || parsed === currentLemma.toLowerCase()) {
        return null;
      }
      return {
        ...note,
        confused_with: parsed,
      };
    })
    .filter((note): note is ConfusionNote => note !== null);
}

type SelectionCategory = "due" | "weak" | "strong" | "recent";

interface SelectionQuota {
  due: number;
  weak: number;
  strong: number;
  recent: number;
}

const DEFAULT_QUOTA: SelectionQuota = {
  due: 0.4,
  weak: 0.3,
  strong: 0.2,
  recent: 0.1,
};

interface QuizEligibleEntry {
  entry: VocabEntry;
  card: SRSCard;
  skillType: SkillType | null;
  skillState: SkillState | null;
  category: SelectionCategory;
}

function interleaveBuckets(
  buckets: Record<SelectionCategory, QuizEligibleEntry[]>,
  targetCount: number,
  quota: SelectionQuota,
): QuizEligibleEntry[] {
  const result: QuizEligibleEntry[] = [];
  const indices: Record<SelectionCategory, number> = {
    due: 0,
    weak: 0,
    strong: 0,
    recent: 0,
  };
  const categories: SelectionCategory[] = ["due", "weak", "strong", "recent"];

  while (result.length < targetCount) {
    const available = categories.filter(
      (cat) => indices[cat] < buckets[cat].length,
    );
    if (available.length === 0) break;

    const totalWeight = available.reduce((sum, cat) => sum + quota[cat], 0);
    let rand = Math.random() * totalWeight;
    let chosen: SelectionCategory = available[0];

    for (const cat of available) {
      rand -= quota[cat];
      if (rand <= 0) {
        chosen = cat;
        break;
      }
    }

    result.push(buckets[chosen][indices[chosen]++]);
  }

  return shuffleArray(result);
}

async function getQuizEligibleEntries(
  config: QuizConfig,
): Promise<QuizEligibleEntry[]> {
  const allCards = shuffleArray(getAllCards());
  if (allCards.length === 0) return [];

  const now = new Date();
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  const buckets: Record<SelectionCategory, QuizEligibleEntry[]> = {
    due: [],
    weak: [],
    strong: [],
    recent: [],
  };

  const seenKeys = new Set<string>();

  let processedCount = 0;
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

    // Apply level and official filters
    // Phrases don't have level or official_list properties, so skip them if these filters are active
    const hasLevelFilter = config.levelFilter && config.levelFilter.length > 0;
    const hasOfficialFilter = config.officialOnly;
    
    if (isWordEntry(entry)) {
      if (hasLevelFilter && (entry.level === null || !config.levelFilter!.includes(entry.level))) {
        continue;
      }
      if (hasOfficialFilter && !entry.in_official_list) {
        continue;
      }
    } else if (hasLevelFilter || hasOfficialFilter) {
      // Phrases are excluded when level or official filters are active
      continue;
    }

    processedCount++;
    if (processedCount % 50 === 0) {
      await yieldToMain();
    }

    if (card.skills) {
      for (const [skill, state] of Object.entries(card.skills)) {
        if (!state) continue;
        const skillType = skill as SkillType;
        const key = `${card.lemma}::${card.sense_id}::${skillType}`;
        if (seenKeys.has(key)) continue;
        seenKeys.add(key);

        const isDue = new Date(state.due) <= now;
        const isWeak = state.lapses >= 2 || state.stability < 3;
        const isStrong = state.stability >= 21;
        const isRecent =
          state.last_review && new Date(state.last_review) >= oneDayAgo;

        let category: SelectionCategory;
        if (isDue) category = "due";
        else if (isWeak) category = "weak";
        else if (isRecent) category = "recent";
        else if (isStrong) category = "strong";
        else continue;

        buckets[category].push({
          entry,
          card,
          skillType,
          skillState: state,
          category,
        });
      }
    }

    const newSkills = getNewSkillsForCard(card);
    for (const skill of newSkills) {
      const key = `${card.lemma}::${card.sense_id}::${skill}`;
      if (seenKeys.has(key)) continue;
      seenKeys.add(key);

      buckets.due.push({
        entry,
        card,
        skillType: skill,
        skillState: null,
        category: "due",
      });
    }

    const mainKey = `${card.lemma}::${card.sense_id}::main`;
    if (seenKeys.has(mainKey)) continue;
    seenKeys.add(mainKey);

    const isDue = new Date(card.due) <= now;
    const isWeak = card.lapses >= 2 || card.stability < 3;
    const isStrong = card.stability >= 21;
    const isRecent =
      card.last_review && new Date(card.last_review) >= oneDayAgo;

    let category: SelectionCategory;
    if (isDue) category = "due";
    else if (isWeak) category = "weak";
    else if (isRecent) category = "recent";
    else if (isStrong) category = "strong";
    else continue;

    buckets[category].push({
      entry,
      card,
      skillType: null,
      skillState: null,
      category,
    });
  }

  for (const cat of Object.keys(buckets) as SelectionCategory[]) {
    buckets[cat] = shuffleArray(buckets[cat]);
  }

  return interleaveBuckets(buckets, config.count * 2, DEFAULT_QUOTA);
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

  if (type === "word") {
    const validNotes = getValidConfusionNotes(entry.confusion_notes, entry.lemma);
    for (const note of validNotes) {
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

function findAllLemmaMatches(
  text: string,
  lemma: string,
  isPhrase: boolean,
): { match: string; index: number }[] {
  const lemmaLower = lemma.toLowerCase();

  if (isPhrase) {
    const forms = getAllPhraseForms(lemma);
    const escapedForms = Array.from(forms).map(escapeRegex);
    const pattern = new RegExp(`\\b(${escapedForms.join("|")})\\b`, "gi");
    const matches: { match: string; index: number }[] = [];
    let result;
    while ((result = pattern.exec(text)) !== null) {
      matches.push({ match: result[1], index: result.index });
    }
    return matches;
  }

  const wordPattern = /\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b/g;
  const matches: { match: string; index: number }[] = [];
  let wordMatch;

  while ((wordMatch = wordPattern.exec(text)) !== null) {
    const word = wordMatch[0];
    const baseForms = getBaseForms(word);

    if (baseForms.includes(lemmaLower)) {
      matches.push({ match: word, index: wordMatch.index });
    }
  }

  return matches;
}

function extractInflectedForm(
  text: string,
  lemma: string,
  isPhrase: boolean,
): string | null {
  const matches = findAllLemmaMatches(text, lemma, isPhrase);
  return matches.length > 0 ? matches[0].match : null;
}

function blankOutLemma(
  text: string,
  lemma: string,
  isPhrase: boolean,
): string {
  const matches = findAllLemmaMatches(text, lemma, isPhrase);

  if (matches.length === 0) {
    return text;
  }

  let result = text;
  for (let i = matches.length - 1; i >= 0; i--) {
    const { match, index } = matches[i];
    result = result.slice(0, index) + "_______" + result.slice(index + match.length);
  }

  return result;
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
  const example = selectBestExample(sense.examples, { quizType: "fill_blank" });
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
  const example = selectBestExample(sense.examples, { quizType: "spelling" });
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
  const validNotes = getValidConfusionNotes(entry.confusion_notes, entry.lemma);
  const confusionNote = validNotes.length > 0 ? validNotes[0] : null;

  const example = selectBestExample(sense.examples, { quizType: "distinction" });
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

  for (let i = 0; i < shuffledSelected.length; i++) {
    const { entry, card, skillType } = shuffledSelected[i];
    if (!entry.senses || entry.senses.length === 0) continue;

    const sense = entry.senses[0];

    let quizType: QuizQuestionType;
    if (config.force_types && config.force_types.length > 0) {
      quizType =
        config.force_types[Math.floor(Math.random() * config.force_types.length)];
    } else if (skillType) {
      quizType = skillTypeToQuizType(skillType);
    } else {
      // When skillType is null, use the card's SRS state to determine quiz type
      // getQuizTypeForCard considers stability, reps, lapses, and state
      quizType = getQuizTypeForCard(card);
    }

    const question = await generateQuestion(entry, sense, quizType);
    question.sense_id = card.sense_id;
    questions.push(question);

    if ((i + 1) % 5 === 0) {
      await yieldToMain();
    }
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

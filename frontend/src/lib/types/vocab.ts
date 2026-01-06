export type VocabType = "word" | "phrase" | "pattern";

export type ExamType =
  | "gsat"
  | "gsat_makeup"
  | "ast"
  | "ast_makeup"
  | "gsat_trial"
  | "gsat_ref";

export type SectionType =
  | "vocabulary"
  | "cloze"
  | "discourse"
  | "structure"
  | "reading"
  | "translation"
  | "mixed";

export type AnnotationRole =
  | "correct_answer"
  | "distractor"
  | "notable_phrase"
  | "notable_pattern"
  | "none";

export type SentenceRole =
  | "cloze"
  | "passage"
  | "option"
  | "question"
  | "translation";

export type PatternCategory =
  | "subjunctive"
  | "inversion"
  | "participle"
  | "cleft_sentence"
  | "comparison_adv"
  | "concession_adv"
  | "result_purpose";

export type PatternSubtype =
  | "wish_past"
  | "wish_past_perfect"
  | "as_if_as_though"
  | "were_to"
  | "should_subjunctive"
  | "had_subjunctive"
  | "demand_suggest"
  | "if_only"
  | "but_for"
  | "its_time"
  | "negative_adverb"
  | "not_only_but_also"
  | "no_sooner_than"
  | "only_inversion"
  | "so_adj_that"
  | "conditional_inversion"
  | "not_until"
  | "perfect_participle"
  | "with_participle"
  | "absolute_participle"
  | "it_that"
  | "what_cleft"
  | "the_more_the_more"
  | "no_more_than"
  | "times_as"
  | "no_matter"
  | "whatever_however"
  | "adj_as_clause"
  | "so_that_result"
  | "such_that"
  | "lest"
  | "for_fear_that";

export interface SourceInfo {
  year: number;
  exam_type: ExamType;
  section_type: SectionType;
  question_number?: number;
  role?: AnnotationRole;
  sentence_role?: SentenceRole;
}

export interface ExamExample {
  text: string;
  source: SourceInfo;
}

export interface VocabSense {
  sense_id: string;
  pos: string | null;
  zh_def: string;
  en_def: string;
  examples: ExamExample[];
  generated_example: string;
}

export interface FrequencyData {
  total_appearances: number;
  tested_count: number;
  active_tested_count: number;
  year_spread: number;
  years: number[];
  by_role: Record<string, number>;
  by_section: Record<string, number>;
  by_exam_type: Record<string, number>;
  ml_score: number | null;
  importance_score: number;
}

export interface ConfusionNote {
  confused_with: string;
  distinction: string;
  memory_tip: string;
}

export interface RootInfo {
  root_breakdown: string | null;
  memory_strategy: string;
}

export interface PatternSubtypeOutput {
  subtype: PatternSubtype;
  display_name: string;
  structure: string;
  examples: ExamExample[];
  generated_example: string;
}

export interface WordEntry {
  lemma: string;
  pos: string[];
  level: number | null;
  in_official_list: boolean;
  frequency: FrequencyData;
  senses: VocabSense[];
  confusion_notes: ConfusionNote[];
  root_info: RootInfo | null;
  synonyms: string[] | null;
  antonyms: string[] | null;
  derived_forms: string[] | null;
}

export interface PhraseEntry {
  lemma: string;
  frequency: FrequencyData;
  senses: VocabSense[];
  confusion_notes: ConfusionNote[];
  synonyms: string[] | null;
  antonyms: string[] | null;
  derived_forms: string[] | null;
}

export interface PatternEntry {
  lemma: string;
  pattern_category: PatternCategory;
  subtypes: PatternSubtypeOutput[];
  teaching_explanation: string;
}

export type VocabEntryUnion = WordEntry | PhraseEntry | PatternEntry;
export type VocabEntry = WordEntry | PhraseEntry;
export type SRSEligibleEntry = WordEntry | PhraseEntry;

export function isWordEntry(entry: VocabEntryUnion): entry is WordEntry {
  return "pos" in entry && Array.isArray(entry.pos);
}

export function isPhraseEntry(entry: VocabEntryUnion): entry is PhraseEntry {
  return "frequency" in entry && !("pos" in entry) && !("pattern_category" in entry);
}

export function isPatternEntry(entry: VocabEntryUnion): entry is PatternEntry {
  return "pattern_category" in entry;
}

export interface VocabMetadata {
  vocab_hash?: string;
  exam_year_range: Record<string, number>;
  total_entries: number;
  count_by_type: Record<string, number>;
}

export interface VocabDatabase {
  version: string;
  generated_at: string;
  metadata: VocabMetadata;
  words: WordEntry[];
  phrases: PhraseEntry[];
  patterns: PatternEntry[];
}

export interface WordIndexItem {
  lemma: string;
  type: "word";
  pos: string[];
  level: number | null;
  in_official_list: boolean;
  sense_count: number;
  zh_preview: string;
  importance_score: number;
  tested_count: number;
  year_spread: number;
  total_appearances: number;
  primary_pos: string;
}

export interface PhraseIndexItem {
  lemma: string;
  type: "phrase";
  sense_count: number;
  zh_preview: string;
  importance_score: number;
  tested_count: number;
  year_spread: number;
  total_appearances: number;
}

export interface PatternIndexItem {
  lemma: string;
  type: "pattern";
  pattern_category: PatternCategory;
  subtype_count: number;
}

export type VocabIndexItem = WordIndexItem | PhraseIndexItem | PatternIndexItem;

export interface VersionInfo {
  version: string;
  vocab_hash: string;
  generated_at: string;
  entry_count: number;
}

export function createWordIndexItem(entry: WordEntry): WordIndexItem {
  const primarySense = entry.senses?.[0];
  const zhPreview = primarySense?.zh_def ?? "";
  const truncated =
    zhPreview.length > 20 ? zhPreview.slice(0, 20) + "…" : zhPreview;
  const primaryPos = entry.pos?.[0] ?? "";

  return {
    lemma: entry.lemma,
    type: "word",
    pos: entry.pos ?? [],
    level: entry.level,
    in_official_list: entry.in_official_list ?? false,
    sense_count: entry.senses?.length ?? 0,
    zh_preview: truncated,
    importance_score: entry.frequency?.importance_score ?? 0,
    tested_count: entry.frequency?.tested_count ?? 0,
    year_spread: entry.frequency?.year_spread ?? 0,
    total_appearances: entry.frequency?.total_appearances ?? 0,
    primary_pos: primaryPos,
  };
}

export function createPhraseIndexItem(entry: PhraseEntry): PhraseIndexItem {
  const primarySense = entry.senses?.[0];
  const zhPreview = primarySense?.zh_def ?? "";
  const truncated =
    zhPreview.length > 20 ? zhPreview.slice(0, 20) + "…" : zhPreview;

  return {
    lemma: entry.lemma,
    type: "phrase",
    sense_count: entry.senses?.length ?? 0,
    zh_preview: truncated,
    importance_score: entry.frequency?.importance_score ?? 0,
    tested_count: entry.frequency?.tested_count ?? 0,
    year_spread: entry.frequency?.year_spread ?? 0,
    total_appearances: entry.frequency?.total_appearances ?? 0,
  };
}

export function createPatternIndexItem(entry: PatternEntry): PatternIndexItem {
  return {
    lemma: entry.lemma,
    type: "pattern",
    pattern_category: entry.pattern_category,
    subtype_count: entry.subtypes.length,
  };
}

export function isWordIndexItem(item: VocabIndexItem): item is WordIndexItem {
  return item.type === "word";
}

export function isPhraseIndexItem(item: VocabIndexItem): item is PhraseIndexItem {
  return item.type === "phrase";
}

export function isPatternIndexItem(item: VocabIndexItem): item is PatternIndexItem {
  return item.type === "pattern";
}

export function sortSensesByExamFrequency(senses: VocabSense[]): VocabSense[] {
  if (!senses || senses.length === 0) return [];

  return [...senses].sort((a, b) => {
    const aCount = a.examples?.length ?? 0;
    const bCount = b.examples?.length ?? 0;
    return bCount - aCount;
  });
}

export function getPrimarySenseByFrequency(senses: VocabSense[]): VocabSense | null {
  if (!senses || senses.length === 0) return null;
  const sorted = sortSensesByExamFrequency(senses);
  return sorted[0];
}

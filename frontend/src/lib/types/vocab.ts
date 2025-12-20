export type VocabTier =
  | "tested"
  | "translation"
  | "phrase"
  | "pattern"
  | "basic";

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

export type PatternType =
  | "conditional"
  | "subjunctive"
  | "relative_clause"
  | "passive_voice"
  | "inversion"
  | "cleft_sentence"
  | "participle_construction"
  | "emphatic"
  | "other";

export interface SourceInfo {
  year: number;
  exam_type: ExamType;
  section_type: SectionType;
  question_number?: number;
}

export interface ExamExample {
  text: string;
  source: SourceInfo;
}

export interface VocabSense {
  sense_id: string;
  pos: string;
  zh_def: string;
  en_def: string;
  tested_in_exam: boolean;
  examples?: ExamExample[];
  generated_example: string;
}

export interface FrequencyData {
  total_occurrences: number;
  tested_count: number;
  year_spread: number;
  weighted_score: number;
  ml_score: number | null;
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

export interface PatternInfo {
  pattern_type: PatternType;
  display_name: string | null;
  structure: string;
}

export interface VocabEntry {
  lemma: string;
  type: VocabType;
  pos: string[];
  level: number | null;
  tier: VocabTier;
  in_official_list: boolean;
  senses: VocabSense[];
  frequency: FrequencyData;
  confusion_notes: ConfusionNote[];
  root_info: RootInfo | null;
  pattern_info: PatternInfo | null;
  synonyms: string[] | null;
  antonyms: string[] | null;
  derived_forms: string[] | null;
}

export interface DistractorGroup {
  correct_answer: string;
  distractors: string[];
  question_context: string;
  source: SourceInfo;
}

export interface VocabMetadata {
  vocab_hash: string;
  exam_year_range: Record<string, number>;
  total_entries: number;
  count_by_tier: Record<string, number>;
  count_by_type: Record<string, number>;
}

export interface VocabDatabase {
  version: string;
  generated_at: string;
  metadata: VocabMetadata;
  entries: VocabEntry[];
  distractor_groups: DistractorGroup[];
}

export interface VocabIndexItem {
  lemma: string;
  type: VocabType;
  pos: string[];
  level: number | null;
  tier: VocabTier;
  in_official_list: boolean;
  sense_count: number;
  zh_preview: string;
  importance_score: number;
  tested_count: number;
  year_spread: number;
  count: number;
  primary_pos: string;
  meaning_count: number;
}

export interface VersionInfo {
  version: string;
  vocab_hash: string;
  generated_at: string;
  entry_count: number;
}

export function computeImportanceScore(frequency: FrequencyData): number {
  return frequency.ml_score ?? frequency.weighted_score / 30;
}

export function createIndexItem(entry: VocabEntry): VocabIndexItem {
  const primarySense = entry.senses[0];
  const zhPreview = primarySense?.zh_def ?? "";
  const truncated =
    zhPreview.length > 20 ? zhPreview.slice(0, 20) + "…" : zhPreview;
  const primaryPos = entry.pos[0] ?? "";

  return {
    lemma: entry.lemma,
    type: entry.type as VocabType,
    pos: entry.pos,
    level: entry.level,
    tier: entry.tier,
    in_official_list: entry.in_official_list,
    sense_count: entry.senses.length,
    zh_preview: truncated,
    importance_score: computeImportanceScore(entry.frequency),
    tested_count: entry.frequency.tested_count,
    year_spread: entry.frequency.year_spread,
    count: entry.frequency.total_occurrences,
    primary_pos: primaryPos,
    meaning_count: entry.senses.length,
  };
}

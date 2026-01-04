export const EXAM_TYPE_DISPLAY_NAMES: Record<string, string> = {
  gsat: "學測",
  gsat_makeup: "學測補考",
  gsat_trial: "學測試辦",
  gsat_ref: "學測參考試卷",
  ast: "指考",
  ast_makeup: "指考補考",
};

export const SECTION_TYPE_DISPLAY_NAMES: Record<string, string> = {
  vocabulary: "詞彙題",
  vocab: "詞彙題",
  cloze: "綜合測驗",
  discourse: "文意選填",
  structure: "篇章結構",
  reading: "閱讀測驗",
  mixed: "混合題",
  translation: "中譯英",
  composition: "作文",
};

export function formatExamType(examType: string): string {
  return EXAM_TYPE_DISPLAY_NAMES[examType] ?? examType;
}

export function formatSectionType(sectionType: string): string {
  return SECTION_TYPE_DISPLAY_NAMES[sectionType] ?? sectionType;
}

export function formatExamSource(source: {
  year: number;
  exam_type: string;
  section_type: string;
  question_number?: number;
}): string {
  const examType = formatExamType(source.exam_type);
  const section = formatSectionType(source.section_type);
  return `${source.year} ${examType} · ${section}`;
}

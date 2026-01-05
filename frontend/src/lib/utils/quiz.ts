import { EXAM_TYPE_DISPLAY_NAMES, SECTION_TYPE_DISPLAY_NAMES } from "$lib/constants/exam-types";

/**
 * Formats the exam source information into a human-readable string.
 * Example: "112 學測 - 詞彙題"
 */
export function formatExamSource(source?: {
    year: number;
    exam_type: string;
    section_type: string;
}): string {
    if (!source) return "";

    const examName = EXAM_TYPE_DISPLAY_NAMES[source.exam_type] || source.exam_type;
    const sectionName = SECTION_TYPE_DISPLAY_NAMES[source.section_type] || source.section_type;

    return `${source.year} ${examName} · ${sectionName}`;
}

/**
 * Returns a short version of the exam source (e.g., for tags)
 */
export function formatExamSourceShort(source?: {
    year: number;
    exam_type: string;
}): string {
    if (!source) return "";

    const examName = EXAM_TYPE_DISPLAY_NAMES[source.exam_type] || source.exam_type;
    return `${source.year} ${examName}`;
}

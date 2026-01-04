import asyncio
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..llm import STAGE1_EXAMPLES, STAGE1_RULES, STAGE1_SYSTEM, ModelTier, get_llm_client
from ..models import (
    AnnotatedSentence,
    Annotation,
    AnnotationRole,
    EssayTopic,
    ExamType,
    MixedQuestionType,
    PatternCategory,
    PatternSubtype,
    SectionData,
    SectionType,
    SentenceRole,
    StructuredExam,
    TranslationItem,
)

logger = logging.getLogger(__name__)

SENTENCE_ROLE_VALUES = Literal[
    "cloze",
    "passage",
    "question_prompt",
    "option",
    "unused_option",
]

PATTERN_CATEGORY_VALUES = Literal[
    "subjunctive",
    "inversion",
    "participle",
    "cleft_sentence",
    "comparison_adv",
    "concession_adv",
    "result_purpose",
]

PATTERN_SUBTYPE_VALUES = Literal[
    "wish_past",
    "wish_past_perfect",
    "as_if_as_though",
    "were_to",
    "should_subjunctive",
    "had_subjunctive",
    "demand_suggest",
    "if_only",
    "but_for",
    "its_time",
    "negative_adverb",
    "not_only_but_also",
    "no_sooner_than",
    "only_inversion",
    "so_adj_that",
    "conditional_inversion",
    "not_until",
    "perfect_participle",
    "with_participle",
    "absolute_participle",
    "it_that",
    "what_cleft",
    "the_more_the_more",
    "no_more_than",
    "times_as",
    "no_matter",
    "whatever_however",
    "adj_as_clause",
    "so_that_result",
    "such_that",
    "lest",
    "for_fear_that",
]

ANNOTATION_ROLE_VALUES = Literal[
    "correct_answer",
    "distractor",
    "notable_phrase",
    "notable_pattern",
]

MIXED_QUESTION_TYPE_VALUES = Literal[
    "fill_in_word",
    "multiple_select",
    "short_answer",
]


class AnnotationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    surface: Annotated[
        str,
        Field(
            description="For correct_answer/distractor: exact substring from sentence. For notable_phrase: dictionary lemma form (e.g., 'give up' not 'gave up')."
        ),
    ]
    role: Annotated[
        ANNOTATION_ROLE_VALUES,
        Field(
            description="correct_answer: word filling the blank. distractor: wrong option. notable_phrase: phrasal verb with dictionary entry (use lemma). notable_pattern: requires pattern_category + pattern_subtype."
        ),
    ]
    pattern_category: Annotated[
        PATTERN_CATEGORY_VALUES | None,
        Field(
            description="Required for notable_pattern: participle, inversion, comparison_adv, etc."
        ),
    ] = None
    pattern_subtype: Annotated[
        PATTERN_SUBTYPE_VALUES | None,
        Field(
            description="Required for notable_pattern: perfect_participle, conditional_inversion, etc."
        ),
    ] = None


class SentenceOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Annotated[
        str,
        Field(description="Complete sentence with blank filled in. No __N__ markers allowed."),
    ]
    question: Annotated[
        int | None,
        Field(
            description="Question number N from __N__ blank. Required for cloze/question_prompt/option. Null only for passage."
        ),
    ] = None
    sentence_role: Annotated[
        SENTENCE_ROLE_VALUES,
        Field(
            description="cloze: had __N__ blank. passage: context paragraph. question_prompt: 'What is...?'. option: answer choice. unused_option: structure/discourse unused item."
        ),
    ]
    annotations: Annotated[
        list[AnnotationOutput] | None,
        Field(
            description="cloze: 1 correct_answer + 3 distractors. Add notable_phrase/notable_pattern when criteria met."
        ),
    ] = None
    mixed_question_type: Annotated[
        MIXED_QUESTION_TYPE_VALUES | None,
        Field(
            description="For mixed section only: fill_in_word, multiple_select, or short_answer."
        ),
    ] = None
    acceptable_answers: Annotated[
        list[str] | None,
        Field(
            description="For fill_in_word: words from the passage that fit the blank, with appropriate morphological forms applied as needed."
        ),
    ] = None


class SectionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Annotated[
        Literal["vocabulary", "cloze", "discourse", "structure", "reading", "mixed"],
        Field(description="Section type from exam header."),
    ]
    sentences: Annotated[
        list[SentenceOutput],
        Field(description="All sentences in order. Every __N__ blank must have a cloze entry."),
    ]


class TranslationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: Annotated[
        int,
        Field(description="Translation question number (1, 2, etc.)."),
    ]
    chinese_prompt: Annotated[
        str,
        Field(description="Original Chinese sentence to translate."),
    ]
    keywords: Annotated[
        list[str],
        Field(
            description="3-6 key single English words (no spaces, no phrases). Break phrases into separate words."
        ),
    ]


class EssayOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: Annotated[
        str,
        Field(description="Essay topic text starting from '提示：'."),
    ]
    suggested_words: Annotated[
        list[str],
        Field(description="5-10 sophisticated single words for the topic."),
    ]


class StructuredExamOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sections: Annotated[
        list[SectionOutput],
        Field(description="Exam sections in order. Do NOT include translation here."),
    ] = Field(default_factory=list)
    translation_items: Annotated[
        list[TranslationOutput],
        Field(description="Translation questions extracted separately."),
    ] = Field(default_factory=list)
    essay_topics: Annotated[
        list[EssayOutput],
        Field(description="Essay prompts with suggested vocabulary."),
    ] = Field(default_factory=list)


def _parse_section_type(s: str) -> SectionType:
    mapping = {
        "vocabulary": SectionType.VOCABULARY,
        "cloze": SectionType.CLOZE,
        "discourse": SectionType.DISCOURSE,
        "structure": SectionType.STRUCTURE,
        "reading": SectionType.READING,
        "translation": SectionType.TRANSLATION,
        "mixed": SectionType.MIXED,
    }
    return mapping.get(s.lower(), SectionType.MIXED)


def _parse_annotation_role(s: str | None) -> AnnotationRole:
    if not s:
        return AnnotationRole.CORRECT_ANSWER
    mapping = {
        "correct_answer": AnnotationRole.CORRECT_ANSWER,
        "distractor": AnnotationRole.DISTRACTOR,
        "tested_keyword": AnnotationRole.TESTED_KEYWORD,
        "notable_phrase": AnnotationRole.NOTABLE_PHRASE,
        "notable_pattern": AnnotationRole.NOTABLE_PATTERN,
    }
    return mapping.get(s.lower(), AnnotationRole.CORRECT_ANSWER)


def _parse_sentence_role(s: str | None) -> SentenceRole | None:
    if not s:
        return None
    mapping = {
        "cloze": SentenceRole.CLOZE,
        "passage": SentenceRole.PASSAGE,
        "question_prompt": SentenceRole.QUESTION_PROMPT,
        "option": SentenceRole.OPTION,
        "unused_option": SentenceRole.UNUSED_OPTION,
    }
    return mapping.get(s.lower())


def _parse_pattern_category(s: str | None) -> PatternCategory | None:
    if not s:
        return None
    mapping = {
        "subjunctive": PatternCategory.SUBJUNCTIVE,
        "inversion": PatternCategory.INVERSION,
        "participle": PatternCategory.PARTICIPLE,
        "cleft_sentence": PatternCategory.CLEFT_SENTENCE,
        "comparison_adv": PatternCategory.COMPARISON_ADV,
        "concession_adv": PatternCategory.CONCESSION_ADV,
        "result_purpose": PatternCategory.RESULT_PURPOSE,
    }
    return mapping.get(s.lower())


def _parse_pattern_subtype(s: str | None) -> PatternSubtype | None:
    if not s:
        return None
    mapping = {
        "wish_past": PatternSubtype.SUBJ_WISH_PAST,
        "wish_past_perfect": PatternSubtype.SUBJ_WISH_PAST_PERFECT,
        "as_if_as_though": PatternSubtype.SUBJ_AS_IF,
        "were_to": PatternSubtype.SUBJ_WERE_TO,
        "should_subjunctive": PatternSubtype.SUBJ_SHOULD,
        "had_subjunctive": PatternSubtype.SUBJ_HAD,
        "demand_suggest": PatternSubtype.SUBJ_DEMAND,
        "if_only": PatternSubtype.SUBJ_IF_ONLY,
        "but_for": PatternSubtype.SUBJ_BUT_FOR,
        "its_time": PatternSubtype.SUBJ_ITS_TIME,
        "negative_adverb": PatternSubtype.INV_NEGATIVE,
        "not_only_but_also": PatternSubtype.INV_NOT_ONLY,
        "no_sooner_than": PatternSubtype.INV_NO_SOONER,
        "only_inversion": PatternSubtype.INV_ONLY,
        "so_adj_that": PatternSubtype.INV_SO_ADJ,
        "conditional_inversion": PatternSubtype.INV_CONDITIONAL,
        "not_until": PatternSubtype.INV_NOT_UNTIL,
        "perfect_participle": PatternSubtype.PART_PERFECT,
        "with_participle": PatternSubtype.PART_WITH,
        "absolute_participle": PatternSubtype.PART_ABSOLUTE,
        "it_that": PatternSubtype.CLEFT_IT_THAT,
        "what_cleft": PatternSubtype.CLEFT_WHAT,
        "the_more_the_more": PatternSubtype.COMP_THE_MORE,
        "no_more_than": PatternSubtype.COMP_NO_MORE_THAN,
        "times_as": PatternSubtype.COMP_TIMES,
        "no_matter": PatternSubtype.CONC_NO_MATTER,
        "whatever_however": PatternSubtype.CONC_WHATEVER,
        "adj_as_clause": PatternSubtype.CONC_ADJ_AS,
        "so_that_result": PatternSubtype.RES_SO_THAT,
        "such_that": PatternSubtype.RES_SUCH_THAT,
        "lest": PatternSubtype.PURP_LEST,
        "for_fear_that": PatternSubtype.PURP_FOR_FEAR,
    }
    return mapping.get(s.lower())


def _parse_mixed_question_type(s: str | None) -> MixedQuestionType | None:
    if not s:
        return None
    mapping = {
        "fill_in_word": MixedQuestionType.FILL_IN_WORD,
        "multiple_select": MixedQuestionType.MULTIPLE_SELECT,
        "short_answer": MixedQuestionType.SHORT_ANSWER,
    }
    return mapping.get(s.lower())


def _convert_annotation(a: AnnotationOutput) -> Annotation:
    return Annotation(
        surface=a.surface,
        role=_parse_annotation_role(a.role),
        pattern_category=_parse_pattern_category(a.pattern_category),
        pattern_subtype=_parse_pattern_subtype(a.pattern_subtype),
    )


def _convert_sentence(s: SentenceOutput) -> AnnotatedSentence:
    return AnnotatedSentence(
        text=s.text,
        question=s.question,
        sentence_role=_parse_sentence_role(s.sentence_role),
        annotations=[_convert_annotation(a) for a in s.annotations] if s.annotations else None,
        mixed_question_type=_parse_mixed_question_type(s.mixed_question_type),
        acceptable_answers=s.acceptable_answers,
    )


def _convert_output_to_exam(
    output: StructuredExamOutput, year: int, exam_type: ExamType
) -> StructuredExam:
    sections = []
    for sec in output.sections:
        section_type = _parse_section_type(sec.type)
        sentences = [_convert_sentence(s) for s in sec.sentences]
        sections.append(SectionData(type=section_type, sentences=sentences))

    essay_topics = [
        EssayTopic(description=e.description, suggested_words=e.suggested_words)
        for e in output.essay_topics
    ]

    translation_items = [
        TranslationItem(
            question=t.question,
            chinese_prompt=t.chinese_prompt,
            keywords=t.keywords,
        )
        for t in output.translation_items
    ]

    return StructuredExam(
        year=year,
        exam_type=exam_type,
        sections=sections,
        essay_topics=essay_topics,
        translation_items=translation_items,
    )


def _detect_relevant_examples(chunk: str) -> list[str]:
    relevant = []
    chunk_lower = chunk.lower()

    if "詞彙題" in chunk or "vocabulary" in chunk_lower:
        relevant.append("vocabulary")
    if "綜合測驗" in chunk or "cloze test" in chunk_lower:
        relevant.append("cloze")
    if "文意選填" in chunk or "discourse" in chunk_lower:
        relevant.append("discourse")
    if "篇章結構" in chunk or "structure" in chunk_lower:
        relevant.append("structure")
    if "閱讀測驗" in chunk or "reading" in chunk_lower:
        relevant.append("reading")
    if "翻譯題" in chunk or "translation" in chunk_lower:
        relevant.append("translation")
    if "混合題" in chunk or "mixed" in chunk_lower:
        relevant.append("mixed")
    if "作文題" in chunk or "writing" in chunk_lower or "composition" in chunk_lower:
        relevant.append("essay")

    return relevant if relevant else ["vocabulary", "cloze"]


def _split_markdown(content: str) -> list[str]:
    parts = re.split(r"(^## .+$)", content, flags=re.MULTILINE)

    chunks = []
    if parts[0].strip():
        chunks.append(parts[0])

    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        chunks.append(header + body)

    return chunks


def _subsplit_chunk(chunk: str) -> list[str]:
    lines = chunk.splitlines()
    header = ""
    body_start = 0

    if lines and lines[0].startswith("##"):
        header = lines[0]
        body_start = 1

    body = "\n".join(lines[body_start:])

    parts = re.split(
        r"(^(?:### )?(?:第\s*\d+.*題為題組|Questions?\s+\d+\s*(?:[-–~]|to)\s*\d+).*$)",
        body,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    if len(parts) < 2:
        if len(chunk) > 4500:
            logger.warning(
                f"Chunk is very large ({len(chunk)} chars) but no question groups found. "
                f"Content start: {chunk[:100]}..."
            )
        return [chunk]

    subchunks = []
    intro = parts[0]

    for i in range(1, len(parts), 2):
        delim = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""

        group_text = delim + "\n" + content

        if i == 1:
            full_text = (header + "\n" + intro + "\n" + group_text).strip()
        else:
            full_text = (header + "\n" + group_text).strip()

        subchunks.append(full_text)

    return subchunks


async def structurize_exam(markdown_path: Path, year: int, exam_type: ExamType) -> StructuredExam:
    markdown_content = markdown_path.read_text(encoding="utf-8")
    raw_chunks = _split_markdown(markdown_content)

    chunks = []
    for c in raw_chunks:
        chunks.extend(_subsplit_chunk(c))

    client = get_llm_client()

    async def process_chunk(chunk: str) -> StructuredExamOutput:
        relevant_keys = _detect_relevant_examples(chunk)
        examples_text = "\n\n".join(
            f'<example type="{key}">\n{STAGE1_EXAMPLES[key]}\n</example>'
            for key in relevant_keys
            if key in STAGE1_EXAMPLES
        )

        prompt = f"""{STAGE1_RULES}

<examples>
{examples_text}
</examples>

<exam_metadata>
Year: {year} (民國)
Type: {exam_type.value}
</exam_metadata>

<exam_content>
{chunk}
</exam_content>

Structure this exam section into JSON following the schema and examples provided."""

        try:
            return await client.complete(
                prompt=prompt,
                system=STAGE1_SYSTEM,
                response_model=StructuredExamOutput,
                temperature=0.1,
                tier=ModelTier.SMART,
            )
        except Exception as e:
            logger.error(f"Failed to structurize chunk for {year} {exam_type}: {e}")
            return StructuredExamOutput(sections=[], translation_items=[], essay_topics=[])

    chunk_results = await asyncio.gather(*[process_chunk(chunk) for chunk in chunks])

    merged_sections = []
    merged_translations = []
    merged_topics = []
    for res in chunk_results:
        merged_sections.extend(res.sections)
        merged_translations.extend(res.translation_items)
        merged_topics.extend(res.essay_topics)

    merged_output = StructuredExamOutput(
        sections=merged_sections,
        translation_items=merged_translations,
        essay_topics=merged_topics,
    )
    return _convert_output_to_exam(merged_output, year, exam_type)


async def process_all_markdowns(
    markdown_files: list[tuple[Path, int, ExamType]],
    cache_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
    concurrency: int = 5,
) -> list[StructuredExam]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)

    total = len(markdown_files)
    completed = 0
    lock = asyncio.Lock()

    async def _process_one(md_path: Path, year: int, exam_type: ExamType) -> StructuredExam:
        nonlocal completed
        cache_path = cache_dir / f"{year}_{exam_type.value}.json"

        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    data = json.load(f)
                exam = StructuredExam.model_validate(data)
                async with lock:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)
                return exam
            except Exception:
                pass

        async with sem:
            exam = await structurize_exam(md_path, year, exam_type)

        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(exam.model_dump_json(indent=2, exclude_none=True))

        async with lock:
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        return exam

    tasks = [_process_one(path, year, etype) for path, year, etype in markdown_files]
    results = await asyncio.gather(*tasks)

    results.sort(key=lambda x: (x.year, x.exam_type.value), reverse=True)
    return results

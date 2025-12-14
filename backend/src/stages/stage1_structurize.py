import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ..llm import STAGE1_SYSTEM, ModelTier, get_llm_client
from ..models import (
    AnnotatedSentence,
    Annotation,
    AnnotationRole,
    AnnotationType,
    DistractorRecord,
    EssayTopic,
    ExamType,
    PatternType,
    SectionData,
    SectionType,
    StructuredExam,
)

logger = logging.getLogger(__name__)


class AnnotationOutput(BaseModel):
    surface: str
    type: Literal["word", "phrase", "pattern"]
    pattern_type: (
        Literal[
            "conditional",
            "subjunctive",
            "relative_clause",
            "passive_voice",
            "inversion",
            "cleft_sentence",
            "participle_construction",
            "emphatic",
            "other",
        ]
        | None
    ) = None


class SentenceOutput(BaseModel):
    text: str
    question: int | None = None
    annotations: list[AnnotationOutput]


class DistractorOutput(BaseModel):
    question: int
    context: str
    correct: str
    wrong: list[str]


class SectionOutput(BaseModel):
    type: Literal["vocabulary", "cloze", "discourse", "structure", "reading", "translation"]
    sentences: list[SentenceOutput]
    distractors: list[DistractorOutput]


class EssayOutput(BaseModel):
    description: str
    suggested_words: list[str]


class StructuredExamOutput(BaseModel):
    sections: list[SectionOutput]
    essay_topics: list[EssayOutput]


def _parse_section_type(s: str) -> SectionType:
    mapping = {
        "vocabulary": SectionType.VOCABULARY,
        "cloze": SectionType.CLOZE,
        "discourse": SectionType.DISCOURSE,
        "structure": SectionType.STRUCTURE,
        "paragraph organization": SectionType.STRUCTURE,
        "organization": SectionType.STRUCTURE,
        "reading": SectionType.READING,
        "translation": SectionType.TRANSLATION,
        "mixed": SectionType.MIXED,
    }
    return mapping.get(s.lower(), SectionType.MIXED)


def _parse_annotation_type(s: str) -> AnnotationType:
    mapping = {
        "word": AnnotationType.WORD,
        "phrase": AnnotationType.PHRASE,
        "pattern": AnnotationType.PATTERN,
    }
    return mapping.get(s.lower(), AnnotationType.WORD)


def _derive_role_from_type(annotation_type: AnnotationType) -> AnnotationRole:
    return {
        AnnotationType.WORD: AnnotationRole.TESTED_ANSWER,
        AnnotationType.PHRASE: AnnotationRole.NOTABLE_PHRASE,
        AnnotationType.PATTERN: AnnotationRole.NOTABLE_PATTERN,
    }[annotation_type]


def _parse_pattern_type(s: str | None) -> PatternType | None:
    if not s:
        return None
    mapping = {
        "conditional": PatternType.CONDITIONAL,
        "subjunctive": PatternType.SUBJUNCTIVE,
        "relative_clause": PatternType.RELATIVE_CLAUSE,
        "passive_voice": PatternType.PASSIVE_VOICE,
        "inversion": PatternType.INVERSION,
        "cleft_sentence": PatternType.CLEFT_SENTENCE,
        "participle_construction": PatternType.PARTICIPLE_CONSTRUCTION,
        "emphatic": PatternType.EMPHATIC,
        "other": PatternType.OTHER,
    }
    return mapping.get(s.lower())


def _convert_output_to_exam(
    output: StructuredExamOutput, year: int, exam_type: ExamType
) -> StructuredExam:
    sections = []
    for sec in output.sections:
        section_type = _parse_section_type(sec.type)
        sentences = [
            AnnotatedSentence(
                text=s.text,
                question=s.question,
                annotations=[
                    Annotation(
                        surface=a.surface,
                        type=(ann_type := _parse_annotation_type(a.type)),
                        role=_derive_role_from_type(ann_type),
                        pattern_type=_parse_pattern_type(a.pattern_type),
                    )
                    for a in s.annotations
                ],
            )
            for s in sec.sentences
        ]
        distractors = [
            DistractorRecord(
                question=d.question,
                context=d.context,
                correct=d.correct,
                wrong=d.wrong,
            )
            for d in sec.distractors
        ]
        sections.append(
            SectionData(type=section_type, sentences=sentences, distractors=distractors)
        )

    essay_topics = [
        EssayTopic(description=e.description, suggested_words=e.suggested_words)
        for e in output.essay_topics
    ]

    return StructuredExam(
        year=year,
        exam_type=exam_type,
        sections=sections,
        essay_topics=essay_topics,
    )


def _split_markdown(content: str) -> list[str]:
    # Split by level 2 headers, keeping the delimiter
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

    # Extract header (usually first line)
    if lines and lines[0].startswith("##"):
        header = lines[0]
        body_start = 1

    body = "\n".join(lines[body_start:])

    # Split by question group header
    # Matches:
    # 1. Chinese: "第 41 至 44 題為題組"
    # 2. English: "Questions 41-44", "Questions 41 to 44"
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
    intro = parts[0]  # Text before first group

    # Iterate groups (delimiter + content)
    for i in range(1, len(parts), 2):
        delim = parts[i]
        content = parts[i + 1] if i + 1 < len(parts) else ""

        group_text = delim + "\n" + content

        # For first group, include intro text (if any)
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
        prompt = f"""<exam_metadata>
Year: {year} (民國)
Type: {exam_type.value}
</exam_metadata>

<exam_content>
{chunk}
</exam_content>

Structure this exam section into JSON. Fill in correct answers, record distractors for vocabulary and cloze sections."""

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
            return StructuredExamOutput(sections=[], essay_topics=[])

    chunk_results = await asyncio.gather(*[process_chunk(chunk) for chunk in chunks])

    merged_sections = []
    merged_topics = []
    for res in chunk_results:
        merged_sections.extend(res.sections)
        merged_topics.extend(res.essay_topics)

    merged_output = StructuredExamOutput(sections=merged_sections, essay_topics=merged_topics)
    return _convert_output_to_exam(merged_output, year, exam_type)


async def process_all_markdowns(
    markdown_files: list[tuple[Path, int, ExamType]],
    cache_dir: Path,
    progress_callback: callable = None,
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

        # Try loading from cache
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
                pass  # Parse error or outdated format, regenerate

        async with sem:
            exam = await structurize_exam(md_path, year, exam_type)

        # Save to cache
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(exam.model_dump_json(indent=2, exclude_none=True))

        async with lock:
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        return exam

    tasks = [_process_one(path, year, etype) for path, year, etype in markdown_files]
    results = await asyncio.gather(*tasks)

    # Sort results to be deterministic
    results.sort(key=lambda x: (x.year, x.exam_type), reverse=True)
    return results

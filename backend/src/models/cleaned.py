from enum import Enum

from pydantic import BaseModel, Field

from .exam import (
    AnnotationRole,
    PatternCategory,
    PatternSubtype,
    SentenceRole,
    SourceInfo,
)


class VocabType(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    PATTERN = "pattern"


class LemmaOccurrence(BaseModel):
    pos: str
    surface: str
    sentence: str
    source: SourceInfo


class PatternOccurrence(BaseModel):
    pattern_category: PatternCategory
    pattern_subtype: PatternSubtype | None
    surface: str
    sentence: str
    source: SourceInfo


class FrequencyData(BaseModel):
    total_occurrences: int = Field(
        description="Total number of times this item appeared across all exams."
    )

    tested_count: int = Field(
        description="Number of times this item was directly tested "
        "(as answer, keyword, or distractor, or extracted from option sentences)."
    )

    year_spread: int = Field(description="Number of distinct years this item appeared in.")

    ml_score: float | None = Field(
        default=None,
        description="ML-predicted probability of being tested in future exams (0.0-1.0). "
        "Filled in Stage 6 after all data is processed.",
    )


def is_tested(source: SourceInfo) -> bool:
    if source.role in (
        AnnotationRole.CORRECT_ANSWER,
        AnnotationRole.DISTRACTOR,
        AnnotationRole.TESTED_KEYWORD,
    ):
        return True

    if source.role is None and source.sentence_role == SentenceRole.OPTION:
        return True

    return False


class EssayTopicData(BaseModel):
    description: str
    suggested_words: list[str]
    source: SourceInfo


class CleanedWordEntry(BaseModel):
    lemma: str
    type: VocabType = VocabType.WORD
    level: int | None = Field(
        default=None,
        description="Official difficulty level (1-6) from CEEC wordlist.",
    )
    in_official_list: bool
    pos: list[str]
    occurrences: list[LemmaOccurrence]
    frequency: FrequencyData


class CleanedPhraseEntry(BaseModel):
    lemma: str
    type: VocabType = VocabType.PHRASE
    occurrences: list[LemmaOccurrence]
    frequency: FrequencyData


class CleanedPatternEntry(BaseModel):
    lemma: str
    type: VocabType = VocabType.PATTERN
    pattern_category: PatternCategory
    occurrences: list[PatternOccurrence]
    frequency: FrequencyData


CleanedVocabEntry = CleanedWordEntry | CleanedPhraseEntry | CleanedPatternEntry


class CleanedVocabData(BaseModel):
    entries: list[CleanedVocabEntry]
    essay_topics: list[EssayTopicData] = []

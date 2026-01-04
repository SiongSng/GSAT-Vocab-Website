from enum import Enum

from pydantic import BaseModel, Field

from .exam import (
    PatternCategory,
    PatternSubtype,
    SourceInfo,
)


class VocabType(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    PATTERN = "pattern"


class FrequencyData(BaseModel):
    """Aggregated frequency statistics"""
    total_appearances: int
    tested_count: int
    active_tested_count: int
    year_spread: int
    years: list[int]
    by_role: dict[str, int]
    by_section: dict[str, int]
    by_exam_type: dict[str, int]
    ml_score: float | None = None


class ContextSentence(BaseModel):
    """Sentence context where word actually appears"""
    text: str
    source: SourceInfo
    pos: str
    surface: str


class LemmaOccurrence(BaseModel):
    pos: str
    surface: str
    sentence: str
    source: SourceInfo


class PhraseOccurrence(BaseModel):
    surface: str
    sentence: str
    source: SourceInfo


class PatternOccurrence(BaseModel):
    pattern_subtype: PatternSubtype | None
    surface: str
    sentence: str
    source: SourceInfo


class CleanedWordEntry(BaseModel):
    lemma: str
    level: int | None = Field(
        default=None,
        description="Official difficulty level (1-6) from CEEC wordlist.",
    )
    in_official_list: bool
    pos: list[str]
    frequency: FrequencyData
    contexts: list[ContextSentence]


class CleanedPhraseEntry(BaseModel):
    lemma: str
    frequency: FrequencyData
    contexts: list[ContextSentence]


class CleanedPatternEntry(BaseModel):
    pattern_category: PatternCategory
    occurrences: list[PatternOccurrence]


CleanedVocabEntry = CleanedWordEntry | CleanedPhraseEntry | CleanedPatternEntry


class CleanedVocabData(BaseModel):
    words: list[CleanedWordEntry] = []
    phrases: list[CleanedPhraseEntry] = []
    patterns: list[CleanedPatternEntry] = []

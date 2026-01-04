from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from .cleaned import ContextSentence, FrequencyData, PatternOccurrence
from .exam import PatternCategory, PatternSubtype


class AssignedSense(BaseModel):
    sense_id: str
    source: Literal["dictionaryapi", "llm_generated"]
    pos: str | None = None
    definition: str | None = None
    examples: list[str] = []
    source_metadata: dict | None = None
    contexts: Sequence[ContextSentence] = ()
    merged_definitions: list[str] = []
    core_meaning: str | None = None


class SenseAssignedWordEntry(BaseModel):
    lemma: str
    pos: list[str]
    level: int | None
    in_official_list: bool
    frequency: FrequencyData
    senses: list[AssignedSense]
    contexts: list[ContextSentence] = []


class SenseAssignedPhraseEntry(BaseModel):
    lemma: str
    frequency: FrequencyData
    senses: list[AssignedSense]
    contexts: list[ContextSentence] = []


class PatternSubtypeData(BaseModel):
    subtype: PatternSubtype
    display_name: str
    structure: str
    occurrences: list[PatternOccurrence]


class SenseAssignedPatternEntry(BaseModel):
    lemma: str
    pattern_category: PatternCategory
    subtypes: list[PatternSubtypeData]


SenseAssignedEntry = SenseAssignedWordEntry | SenseAssignedPhraseEntry | SenseAssignedPatternEntry


class SenseAssignedData(BaseModel):
    words: list[SenseAssignedWordEntry] = []
    phrases: list[SenseAssignedPhraseEntry] = []
    patterns: list[SenseAssignedPatternEntry] = []

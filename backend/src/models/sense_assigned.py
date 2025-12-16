from typing import Literal

from pydantic import BaseModel

from .cleaned import FrequencyData, LemmaOccurrence, PatternOccurrence
from .exam import PatternCategory, PatternSubtype


class AssignedSense(BaseModel):
    sense_id: str
    source: Literal["wordnet", "registry"]
    pos: str | None = None
    gloss: str | None = None
    occurrences: list[LemmaOccurrence]


class SenseAssignedWordEntry(BaseModel):
    lemma: str
    type: Literal["word"] = "word"
    pos: list[str]
    level: int | None
    in_official_list: bool
    senses: list[AssignedSense]
    frequency: FrequencyData


class SenseAssignedPhraseEntry(BaseModel):
    lemma: str
    type: Literal["phrase"] = "phrase"
    senses: list[AssignedSense]
    frequency: FrequencyData


class PatternSubtypeData(BaseModel):
    subtype: PatternSubtype
    display_name: str
    structure: str
    occurrences: list[PatternOccurrence]


class SenseAssignedPatternEntry(BaseModel):
    lemma: str
    type: Literal["pattern"] = "pattern"
    pattern_category: PatternCategory
    subtypes: list[PatternSubtypeData]
    frequency: FrequencyData


SenseAssignedEntry = SenseAssignedWordEntry | SenseAssignedPhraseEntry | SenseAssignedPatternEntry


class SenseAssignedData(BaseModel):
    entries: list[SenseAssignedEntry]

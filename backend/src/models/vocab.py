import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .cleaned import FrequencyData
from .exam import PatternCategory, PatternSubtype, SourceInfo


class ExamExample(BaseModel):
    text: str
    source: SourceInfo


class VocabSense(BaseModel):
    sense_id: str
    pos: str | None = None
    zh_def: str
    en_def: str
    examples: list[ExamExample]
    generated_example: str


class ConfusionNote(BaseModel):
    confused_with: str
    distinction: str
    memory_tip: str


class RootInfo(BaseModel):
    root_breakdown: str | None = None
    memory_strategy: str


class WordEntry(BaseModel):
    type: Literal["word"] = "word"
    lemma: str
    pos: list[str]
    level: int | None
    in_official_list: bool
    senses: list[VocabSense]
    frequency: FrequencyData
    confusion_notes: list[ConfusionNote] = []
    root_info: RootInfo | None = None
    synonyms: list[str] | None = None
    antonyms: list[str] | None = None


class PhraseEntry(BaseModel):
    type: Literal["phrase"] = "phrase"
    lemma: str
    senses: list[VocabSense]
    frequency: FrequencyData
    confusion_notes: list[ConfusionNote] = []


class PatternSubtypeOutput(BaseModel):
    subtype: PatternSubtype
    display_name: str
    structure: str
    examples: list[ExamExample]
    generated_example: str


class PatternEntry(BaseModel):
    type: Literal["pattern"] = "pattern"
    lemma: str
    pattern_category: PatternCategory
    subtypes: list[PatternSubtypeOutput]
    teaching_explanation: str
    frequency: FrequencyData


VocabEntry = WordEntry | PhraseEntry | PatternEntry


class VocabMetadata(BaseModel):
    exam_year_range: dict[str, int]
    total_entries: int
    count_by_type: dict[str, int]


class VocabDatabase(BaseModel):
    version: str
    generated_at: str
    metadata: VocabMetadata
    entries: list[VocabEntry]


class OfficialWordEntry(BaseModel):
    word: str = ""
    parts_of_speech: list[str] = []
    level: str = ""

    class Config:
        populate_by_name = True

    @classmethod
    def from_json(cls, data: dict) -> "OfficialWordEntry":
        return cls(
            word=data.get("Word", ""),
            parts_of_speech=data.get("PartsOfSpeech", []),
            level=data.get("Level", ""),
        )


def load_official_wordlist(path: Path) -> dict[str, OfficialWordEntry]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    if isinstance(data, dict):
        for word, info in data.items():
            result[word.lower()] = OfficialWordEntry(
                word=word,
                parts_of_speech=info.get("pos", []),
                level=str(info.get("level", "")),
            )
    else:
        for entry in data:
            result[entry["Word"].lower()] = OfficialWordEntry.from_json(entry)

    return result

import json
from pathlib import Path

from pydantic import BaseModel

from .cleaned import DistractorGroup, FrequencyData, VocabTier
from .exam import PatternType, SourceInfo


class ExamExample(BaseModel):
    text: str
    source: SourceInfo


class VocabSense(BaseModel):
    sense_id: str
    pos: str
    zh_def: str
    en_def: str
    tested_in_exam: bool
    examples: list[ExamExample]
    generated_example: str


class ConfusionNote(BaseModel):
    confused_with: str
    distinction: str
    memory_tip: str


class RootInfo(BaseModel):
    root_breakdown: str | None = None
    memory_strategy: str


class PatternInfo(BaseModel):
    pattern_type: PatternType
    display_name: str | None
    structure: str


class VocabEntry(BaseModel):
    lemma: str
    type: str
    pos: list[str]
    level: int | None
    tier: VocabTier
    in_official_list: bool
    senses: list[VocabSense]
    frequency: FrequencyData
    confusion_notes: list[ConfusionNote]
    root_info: RootInfo | None = None
    pattern_info: PatternInfo | None = None
    synonyms: list[str] | None = None
    antonyms: list[str] | None = None
    derived_forms: list[str] | None = None


class VocabMetadata(BaseModel):
    exam_year_range: dict[str, int]
    total_entries: int
    count_by_tier: dict[str, int]
    count_by_type: dict[str, int]


class VocabDatabase(BaseModel):
    version: str
    generated_at: str
    metadata: VocabMetadata
    entries: list[VocabEntry]
    distractor_groups: list[DistractorGroup] = []


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

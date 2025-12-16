from pydantic import BaseModel, Field

from .exam import AnnotationRole, PatternCategory, PatternSubtype, SourceInfo


class LemmaOccurrence(BaseModel):
    pos: str
    surface: str
    sentence: str
    role: AnnotationRole
    source: SourceInfo


class ScoredExample(BaseModel):
    text: str
    source: SourceInfo
    role: AnnotationRole
    srs_score: int = Field(ge=0, le=5)


class ExamUsage(BaseModel):
    usage_id: str
    pos: str
    brief_def: str
    examples: list[ScoredExample]


class ConfusionNote(BaseModel):
    confused_with: str
    distinction: str
    memory_tip: str


class PatternInfo(BaseModel):
    pattern_category: PatternCategory
    pattern_subtype: PatternSubtype | None = None
    display_name: str | None
    structure: str


class ExamUsageAnalysis(BaseModel):
    lemma: str
    type: str  # 'word' | 'phrase' | 'pattern'
    pos: list[str]
    usages: list[ExamUsage]
    confusion_notes: list[ConfusionNote]
    pattern_info: PatternInfo | None = None


class RootAnalysis(BaseModel):
    lemma: str
    has_useful_root: bool
    root_breakdown: str | None = None
    memory_strategy: str

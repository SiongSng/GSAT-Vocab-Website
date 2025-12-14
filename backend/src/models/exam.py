from enum import Enum

from pydantic import BaseModel


class ExamType(str, Enum):
    GSAT = "gsat"
    GSAT_MAKEUP = "gsat_makeup"
    AST = "ast"
    AST_MAKEUP = "ast_makeup"
    GSAT_TRIAL = "gsat_trial"
    GSAT_REF = "gsat_ref"


class SectionType(str, Enum):
    VOCABULARY = "vocabulary"
    CLOZE = "cloze"
    DISCOURSE = "discourse"
    STRUCTURE = "structure"
    READING = "reading"
    TRANSLATION = "translation"
    MIXED = "mixed"


class AnnotationType(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    PATTERN = "pattern"


class AnnotationRole(str, Enum):
    TESTED_ANSWER = "tested_answer"
    TESTED_KEYWORD = "tested_keyword"
    TESTED_DISTRACTOR = "tested_distractor"
    PASSAGE_WORD = "passage_word"
    NOTABLE_PHRASE = "notable_phrase"
    NOTABLE_PATTERN = "notable_pattern"


class PatternType(str, Enum):
    CONDITIONAL = "conditional"
    SUBJUNCTIVE = "subjunctive"
    RELATIVE_CLAUSE = "relative_clause"
    PASSIVE_VOICE = "passive_voice"
    INVERSION = "inversion"
    CLEFT_SENTENCE = "cleft_sentence"
    PARTICIPLE_CONSTRUCTION = "participle_construction"
    EMPHATIC = "emphatic"
    OTHER = "other"


class SourceInfo(BaseModel):
    year: int
    exam_type: ExamType
    section_type: SectionType
    question_number: int | None = None


class Annotation(BaseModel):
    surface: str
    type: AnnotationType
    role: AnnotationRole
    pattern_type: PatternType | None = None


class AnnotatedSentence(BaseModel):
    text: str
    question: int | None = None
    annotations: list[Annotation]


class DistractorRecord(BaseModel):
    question: int
    context: str
    correct: str
    wrong: list[str]


class SectionData(BaseModel):
    type: SectionType
    sentences: list[AnnotatedSentence]
    distractors: list[DistractorRecord]


class EssayTopic(BaseModel):
    description: str
    suggested_words: list[str]


class StructuredExam(BaseModel):
    year: int
    exam_type: ExamType
    sections: list[SectionData]
    essay_topics: list[EssayTopic]


# Legacy SourceInfo with question_numbers for backward compatibility during migration
class LegacySourceInfo(BaseModel):
    year: int
    exam_type: ExamType
    section_type: SectionType
    question_numbers: list[int]


class LegacyAnnotatedSentence(BaseModel):
    text: str
    annotations: list[Annotation]
    source: LegacySourceInfo


class LegacyDistractorRecord(BaseModel):
    correct_answer: str
    distractors: list[str]
    question_context: str
    source: LegacySourceInfo


class LegacyStructuredExam(BaseModel):
    year: int
    exam_type: ExamType
    sentences: list[LegacyAnnotatedSentence]
    distractors: list[LegacyDistractorRecord]
    essay_topics: list[EssayTopic]

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


class SentenceRole(str, Enum):
    CLOZE = "cloze"
    PASSAGE = "passage"
    QUESTION_PROMPT = "question_prompt"
    OPTION = "option"
    UNUSED_OPTION = "unused_option"


class AnnotationType(str, Enum):
    WORD = "word"
    PHRASE = "phrase"
    PATTERN = "pattern"


class AnnotationRole(str, Enum):
    CORRECT_ANSWER = "correct_answer"
    DISTRACTOR = "distractor"
    TESTED_KEYWORD = "tested_keyword"
    NOTABLE_PHRASE = "notable_phrase"
    NOTABLE_PATTERN = "notable_pattern"


class PatternCategory(str, Enum):
    SUBJUNCTIVE = "subjunctive"
    INVERSION = "inversion"
    PARTICIPLE = "participle"
    CLEFT_SENTENCE = "cleft_sentence"
    COMPARISON_ADV = "comparison_adv"
    CONCESSION_ADV = "concession_adv"
    RESULT_PURPOSE = "result_purpose"


class PatternSubtype(str, Enum):
    SUBJ_WISH_PAST = "wish_past"
    SUBJ_WISH_PAST_PERFECT = "wish_past_perfect"
    SUBJ_AS_IF = "as_if_as_though"
    SUBJ_WERE_TO = "were_to"
    SUBJ_SHOULD = "should_subjunctive"
    SUBJ_HAD = "had_subjunctive"
    SUBJ_DEMAND = "demand_suggest"
    SUBJ_IF_ONLY = "if_only"
    SUBJ_BUT_FOR = "but_for"
    SUBJ_ITS_TIME = "its_time"

    INV_NEGATIVE = "negative_adverb"
    INV_NOT_ONLY = "not_only_but_also"
    INV_NO_SOONER = "no_sooner_than"
    INV_ONLY = "only_inversion"
    INV_SO_ADJ = "so_adj_that"
    INV_CONDITIONAL = "conditional_inversion"
    INV_NOT_UNTIL = "not_until"

    PART_PERFECT = "perfect_participle"
    PART_WITH = "with_participle"
    PART_ABSOLUTE = "absolute_participle"

    CLEFT_IT_THAT = "it_that"
    CLEFT_WHAT = "what_cleft"

    COMP_THE_MORE = "the_more_the_more"
    COMP_NO_MORE_THAN = "no_more_than"
    COMP_TIMES = "times_as"

    CONC_NO_MATTER = "no_matter"
    CONC_WHATEVER = "whatever_however"
    CONC_ADJ_AS = "adj_as_clause"

    RES_SO_THAT = "so_that_result"
    RES_SUCH_THAT = "such_that"
    PURP_LEST = "lest"
    PURP_FOR_FEAR = "for_fear_that"


class MixedQuestionType(str, Enum):
    FILL_IN_WORD = "fill_in_word"
    MULTIPLE_SELECT = "multiple_select"
    SHORT_ANSWER = "short_answer"


class SourceInfo(BaseModel):
    year: int
    exam_type: ExamType
    section_type: SectionType
    question_number: int | None = None
    role: AnnotationRole | None = None
    sentence_role: SentenceRole | None = None


class Annotation(BaseModel):
    surface: str
    type: AnnotationType
    role: AnnotationRole
    pattern_category: PatternCategory | None = None
    pattern_subtype: PatternSubtype | None = None


class AnnotatedSentence(BaseModel):
    text: str
    question: int | None = None
    sentence_role: SentenceRole | None = None
    annotations: list[Annotation] | None = None
    mixed_question_type: MixedQuestionType | None = None
    acceptable_answers: list[str] | None = None


class SectionData(BaseModel):
    type: SectionType
    sentences: list[AnnotatedSentence]


class EssayTopic(BaseModel):
    description: str
    suggested_words: list[str]


class TranslationItem(BaseModel):
    question: int
    chinese_prompt: str
    keywords: list[str]


class StructuredExam(BaseModel):
    year: int
    exam_type: ExamType
    sections: list[SectionData]
    essay_topics: list[EssayTopic]
    translation_items: list[TranslationItem]

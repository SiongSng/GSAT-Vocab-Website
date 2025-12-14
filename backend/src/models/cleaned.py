"""
Cleaned vocabulary data models.

These models represent the intermediate data format after processing raw exam data.
Used as input for ML training and LLM-based vocabulary entry generation.
"""

from enum import Enum

from pydantic import BaseModel, Field

from .exam import AnnotationRole, SourceInfo


class VocabTier(str, Enum):
    """
    Classification tier for vocabulary items based on how they appeared in exams.

    Used to prioritize which words to generate detailed entries for.
    """

    TESTED = "tested"
    """Word appeared as a test answer or distractor (highest priority)."""

    TRANSLATION = "translation"
    """Word appeared as a keyword in translation section."""

    PHRASE = "phrase"
    """Multi-word phrase or collocation."""

    PATTERN = "pattern"
    """Grammar pattern or sentence structure."""

    BASIC = "basic"
    """Word appeared only in reading passages (lowest priority)."""


class LemmaOccurrence(BaseModel):
    """A single occurrence of a word in an exam."""

    pos: str
    """Part of speech (NOUN, VERB, ADJ, ADV, PHRASE)."""

    surface: str
    """The actual word form as it appeared in the text."""

    sentence: str
    """The sentence containing this word."""

    role: AnnotationRole
    """The role this word played (tested_answer, passage_word, etc.)."""

    source: SourceInfo
    """Exam source information (year, exam type, section)."""


class FrequencyData(BaseModel):
    """
    Frequency and importance metrics for a vocabulary item.

    Contains both legacy rule-based scores and ML-predicted scores.
    Frontend should prefer ml_score when available, falling back to weighted_score.
    """

    total_occurrences: int = Field(
        description="Total number of times this word appeared across all exams."
    )

    tested_count: int = Field(
        description="Number of times this word was directly tested "
        "(as answer, keyword, or distractor). "
        "Higher values indicate words frequently chosen by exam creators."
    )

    year_spread: int = Field(
        description="Number of distinct years this word appeared in. "
        "Higher spread suggests consistent importance across exam cycles."
    )

    weighted_score: float = Field(
        description="Legacy rule-based importance score (0-30 typical range). "
        "Calculated using hand-tuned weights for: "
        "role (answer > keyword > passage), "
        "section (vocabulary > reading > cloze), "
        "recency (recent years weighted higher), "
        "official wordlist membership. "
        "Use this as fallback when ml_score is None."
    )

    ml_score: float | None = Field(
        default=None,
        description="ML-predicted probability of being tested in future exams (0.0-1.0). "
        "Trained on 71 features including temporal patterns, linguistic features, "
        "and distractor analysis. "
        "CV AUC ~0.77 on held-out years. "
        "None if the word lacks sufficient historical data for prediction "
        "(e.g., only appeared in the target year or only in AST exams). "
        "Frontend should use: ml_score ?? (weighted_score / 30) for unified 0-1 scale.",
    )


class DistractorGroup(BaseModel):
    """
    A group of answer choices from a vocabulary question.

    Useful for identifying commonly confused word pairs.
    """

    correct_answer: str
    """The correct answer for this question."""

    distractors: list[str]
    """The incorrect options (typically 3 wrong answers)."""

    question_context: str
    """The sentence or context where the blank appeared."""

    source: SourceInfo
    """Exam source information."""


class EssayTopicData(BaseModel):
    """
    Essay writing topic with suggested vocabulary.

    These suggested words represent what CEEC considers important
    for students to know for writing tasks.
    """

    description: str
    """The essay prompt description (in Chinese)."""

    suggested_words: list[str]
    """Vocabulary words suggested for this topic by the exam creators."""

    source: SourceInfo
    """Exam source information."""


class CleanedVocabEntry(BaseModel):
    """
    A processed vocabulary entry ready for ML training or LLM generation.

    Aggregates all occurrences of a lemma across all exams.
    """

    lemma: str
    """The dictionary form of the word."""

    tier: VocabTier
    """Classification tier based on how the word appeared."""

    level: int | None = Field(
        default=None,
        description="Official difficulty level (1-6) from CEEC wordlist. "
        "1-2: basic, 3-4: intermediate, 5-6: advanced. "
        "None if not in official wordlist.",
    )

    in_official_list: bool
    """Whether this word is in the official CEEC vocabulary list."""

    pos: list[str]
    """Parts of speech this word appeared as (e.g., ['NOUN', 'VERB'])."""

    occurrences: list[LemmaOccurrence]
    """All occurrences of this word across exams."""

    frequency: FrequencyData
    """Frequency metrics and importance scores."""


class CleanedVocabData(BaseModel):
    """
    Complete cleaned vocabulary dataset.

    This is the main output of Stage 2 (clean_and_classify) and input for:
    - Stage 2.5: ML model training
    - Stage 3: LLM-based entry generation
    """

    entries: list[CleanedVocabEntry]
    """
    All vocabulary entries, sorted by importance.
    When ML is enabled: sorted by (ml_score desc, weighted_score desc).
    When using legacy: sorted by weighted_score desc.
    """

    distractor_groups: list[DistractorGroup]
    """All answer choice groups for confusability analysis."""

    essay_topics: list[EssayTopicData]
    """Essay topics with suggested vocabulary."""

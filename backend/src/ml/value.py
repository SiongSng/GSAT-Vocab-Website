"""
Multi-dimensional vocabulary learning value estimation.

Implements TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
and EVL (Expected Value of Learning) frameworks for estimating the true learning
value of each vocabulary item for GSAT exam preparation.

Key insight: The goal is not just "predict if tested" but "estimate learning ROI"
- Recognition value: Can the student understand when reading?
- Production value: Can the student use in writing/translation?
- Discrimination value: Can the student distinguish similar words?
"""

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from ..models.exam import AnnotationRole, ExamType, SectionType


class LearningDimension(Enum):
    """Dimensions of vocabulary learning value"""
    RECOGNITION = "recognition"      # Reading comprehension
    PRODUCTION = "production"        # Writing/translation
    DISCRIMINATION = "discrimination"  # Distinguishing similar words
    RECENCY = "recency"             # Temporal relevance
    DIFFICULTY_MATCH = "difficulty"  # Appropriate difficulty level


@dataclass
class DimensionScore:
    """Score for a single learning dimension"""
    raw_value: float
    normalized_value: float = 0.0
    weight: float = 1.0

    @property
    def weighted_value(self) -> float:
        return self.normalized_value * self.weight


@dataclass
class VocabValue:
    """Comprehensive vocabulary learning value assessment"""
    lemma: str
    level: int | None

    # Dimension scores
    recognition: DimensionScore = field(default_factory=lambda: DimensionScore(0.0))
    production: DimensionScore = field(default_factory=lambda: DimensionScore(0.0))
    discrimination: DimensionScore = field(default_factory=lambda: DimensionScore(0.0))
    recency: DimensionScore = field(default_factory=lambda: DimensionScore(0.0))
    difficulty_match: DimensionScore = field(default_factory=lambda: DimensionScore(0.0))

    # Derived scores
    topsis_score: float = 0.0
    evl_score: float = 0.0
    final_score: float = 0.0

    # Metadata
    sense_coverage: float = 0.0
    untested_sense_count: int = 0
    highest_risk_sense: str | None = None
    interpretation: str = ""


class VocabValueEstimator:
    """
    Estimates the learning value of vocabulary using TOPSIS and EVL frameworks.

    TOPSIS: Multi-criteria decision analysis that considers distance to ideal
    and anti-ideal solutions across multiple dimensions.

    EVL: Expected Value of Learning that considers exam scenarios and
    ability requirements.
    """

    # Default dimension weights (can be learned or tuned)
    DEFAULT_WEIGHTS = {
        LearningDimension.RECOGNITION: 0.25,
        LearningDimension.PRODUCTION: 0.35,  # Higher - direct score impact
        LearningDimension.DISCRIMINATION: 0.15,
        LearningDimension.RECENCY: 0.15,
        LearningDimension.DIFFICULTY_MATCH: 0.10,
    }

    # Exam scenario probabilities (from historical data)
    SCENARIO_PROBS = {
        "reading": 0.35,
        "cloze": 0.25,
        "vocabulary_choice": 0.15,
        "translation": 0.15,
        "discourse": 0.10,
    }

    # Scenario ability requirements
    SCENARIO_ABILITIES = {
        "reading": {"recognition": 0.9, "production": 0.0},
        "cloze": {"recognition": 0.5, "production": 0.5},
        "vocabulary_choice": {"recognition": 1.0, "production": 0.0},
        "translation": {"recognition": 0.3, "production": 0.7},
        "discourse": {"recognition": 0.8, "production": 0.2},
    }

    # Role value weights for production
    # Note: notable_phrase means exam makers flagged this phrase as important
    ROLE_VALUES = {
        AnnotationRole.CORRECT_ANSWER: 2.0,
        AnnotationRole.TESTED_KEYWORD: 3.0,  # Translation keywords are highest
        AnnotationRole.DISTRACTOR: 0.5,
        AnnotationRole.NOTABLE_PHRASE: 1.5,  # Phrases flagged by exam makers
        "notable_phrase": 1.5,  # String fallback for by_role dict
        "none": 0.2,
    }

    # Curriculum cutoff
    CURRICULUM_CUTOFF = 111

    def __init__(
        self,
        target_year: int = 116,
        weights: dict[LearningDimension, float] | None = None,
        student_level: int = 4,  # Target student level (L3-L5 typical)
    ):
        self.target_year = target_year
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.student_level = student_level

        # For TOPSIS normalization
        self._dimension_bounds: dict[LearningDimension, tuple[float, float]] = {}

    def extract_dimensions(self, word_data: dict) -> dict[LearningDimension, DimensionScore]:
        """Extract multi-dimensional value scores from word data"""

        freq = word_data.get("frequency", {})
        contexts = word_data.get("contexts", [])
        level = word_data.get("level") or 0

        # Filter contexts to historical data only
        historical_contexts = [
            c for c in contexts
            if self._is_historically_available(c)
        ]

        scores = {}

        # 1. Recognition Value
        # Words that appear in reading/comprehension contexts
        recognition_value = self._compute_recognition_value(historical_contexts, freq)
        scores[LearningDimension.RECOGNITION] = DimensionScore(
            raw_value=recognition_value,
            weight=self.weights[LearningDimension.RECOGNITION]
        )

        # 2. Production Value
        # Words tested as answers or translation keywords
        production_value = self._compute_production_value(historical_contexts, freq)
        scores[LearningDimension.PRODUCTION] = DimensionScore(
            raw_value=production_value,
            weight=self.weights[LearningDimension.PRODUCTION]
        )

        # 3. Discrimination Value
        # Words that appear as both answer and distractor (confusable)
        discrimination_value = self._compute_discrimination_value(freq)
        scores[LearningDimension.DISCRIMINATION] = DimensionScore(
            raw_value=discrimination_value,
            weight=self.weights[LearningDimension.DISCRIMINATION]
        )

        # 4. Recency Value
        # Recent appearance weighted exponentially
        recency_value = self._compute_recency_value(historical_contexts, freq)
        scores[LearningDimension.RECENCY] = DimensionScore(
            raw_value=recency_value,
            weight=self.weights[LearningDimension.RECENCY]
        )

        # 5. Difficulty Match
        # How well the word matches target student level
        difficulty_value = self._compute_difficulty_match(level)
        scores[LearningDimension.DIFFICULTY_MATCH] = DimensionScore(
            raw_value=difficulty_value,
            weight=self.weights[LearningDimension.DIFFICULTY_MATCH]
        )

        return scores

    def compute_evl(self, word_data: dict) -> float:
        """
        Compute Expected Value of Learning.

        EVL(word) = Σ P(scenario) × V(word | scenario) × Effort_factor(word)
        """
        freq = word_data.get("frequency", {})
        contexts = word_data.get("contexts", [])
        level = word_data.get("level") or 3

        # Estimate ability gains from learning this word
        recognition_gain = self._estimate_recognition_gain(contexts, freq)
        production_gain = self._estimate_production_gain(contexts, freq)

        # Compute expected value across scenarios
        evl = 0.0
        for scenario, prob in self.SCENARIO_PROBS.items():
            abilities = self.SCENARIO_ABILITIES[scenario]
            scenario_value = (
                abilities["recognition"] * recognition_gain +
                abilities["production"] * production_gain
            )
            evl += prob * scenario_value

        # Apply effort factor (easier words have better ROI)
        effort_factor = self._compute_effort_factor(level)

        return evl * effort_factor

    def compute_topsis(
        self,
        all_words: list[dict],
        dimension_scores: list[dict[LearningDimension, DimensionScore]]
    ) -> list[float]:
        """
        Compute TOPSIS scores for all words.

        TOPSIS considers both distance to ideal (best) and anti-ideal (worst)
        solutions across all dimensions.
        """
        if not all_words or not dimension_scores:
            return []

        # Build criteria matrix
        n_words = len(all_words)
        n_dims = len(LearningDimension)

        matrix = np.zeros((n_words, n_dims))
        weights = np.zeros(n_dims)

        for i, scores in enumerate(dimension_scores):
            for j, dim in enumerate(LearningDimension):
                if dim in scores:
                    matrix[i, j] = scores[dim].raw_value
                    weights[j] = scores[dim].weight

        # Handle zero columns
        col_sums = np.sqrt((matrix ** 2).sum(axis=0))
        col_sums[col_sums == 0] = 1.0

        # Vector normalization
        normalized = matrix / col_sums

        # Weighted normalization
        weighted = normalized * weights

        # Ideal and anti-ideal solutions (all dimensions are benefit criteria)
        ideal = weighted.max(axis=0)
        anti_ideal = weighted.min(axis=0)

        # Distance to ideal and anti-ideal
        dist_to_ideal = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
        dist_to_anti = np.sqrt(((weighted - anti_ideal) ** 2).sum(axis=1))

        # Relative closeness (TOPSIS score)
        closeness = dist_to_anti / (dist_to_ideal + dist_to_anti + 1e-10)

        return closeness.tolist()

    def estimate_value(self, word_data: dict) -> VocabValue:
        """
        Compute comprehensive vocabulary value for a single word.
        """
        lemma = word_data.get("lemma", "")
        level = word_data.get("level")
        senses = word_data.get("senses", [])

        # Extract dimension scores
        dimensions = self.extract_dimensions(word_data)

        # Compute EVL
        evl_score = self.compute_evl(word_data)

        # Sense-level analysis
        sense_analysis = self._analyze_senses(senses)

        # Create value object
        value = VocabValue(
            lemma=lemma,
            level=level,
            recognition=dimensions.get(LearningDimension.RECOGNITION, DimensionScore(0.0)),
            production=dimensions.get(LearningDimension.PRODUCTION, DimensionScore(0.0)),
            discrimination=dimensions.get(LearningDimension.DISCRIMINATION, DimensionScore(0.0)),
            recency=dimensions.get(LearningDimension.RECENCY, DimensionScore(0.0)),
            difficulty_match=dimensions.get(LearningDimension.DIFFICULTY_MATCH, DimensionScore(0.0)),
            evl_score=evl_score,
            sense_coverage=sense_analysis.get("coverage", 0.0),
            untested_sense_count=sense_analysis.get("untested_count", 0),
            highest_risk_sense=sense_analysis.get("highest_risk"),
        )

        # Generate interpretation
        value.interpretation = self._generate_interpretation(value, word_data)

        return value

    def estimate_batch(self, words: list[dict]) -> list[VocabValue]:
        """
        Compute vocabulary values for all words with TOPSIS normalization.
        """
        if not words:
            return []

        # First pass: extract dimension scores
        dimension_scores = [self.extract_dimensions(w) for w in words]

        # Compute TOPSIS scores
        topsis_scores = self.compute_topsis(words, dimension_scores)

        # Second pass: create VocabValue objects with all scores
        results = []
        for i, word_data in enumerate(words):
            value = self.estimate_value(word_data)
            value.topsis_score = topsis_scores[i] if i < len(topsis_scores) else 0.0

            # Final score combines TOPSIS and EVL
            value.final_score = (
                0.5 * value.topsis_score +
                0.3 * min(1.0, value.evl_score / 10.0) +  # Normalize EVL
                0.2 * value.sense_coverage  # Bonus for sense coverage
            )

            results.append(value)

        return results

    # === Private methods ===

    def _is_historically_available(self, context: dict) -> bool:
        """Check if context is available before target year"""
        source = context.get("source", {})
        year = context.get("year") or source.get("year", 0)

        if year < self.target_year:
            return True
        if year == self.target_year:
            exam_type = context.get("exam_type") or source.get("exam_type")
            if exam_type in [ExamType.GSAT_REF, ExamType.GSAT_TRIAL]:
                return True
        return False

    def _compute_recognition_value(self, contexts: list[dict], freq: dict) -> float:
        """Compute value for reading comprehension"""
        section_counts = freq.get("by_section", {})

        reading_value = (
            section_counts.get(SectionType.READING, 0) * 0.5 +
            section_counts.get(SectionType.CLOZE, 0) * 0.4 +
            section_counts.get(SectionType.DISCOURSE, 0) * 0.4 +
            section_counts.get(SectionType.VOCABULARY, 0) * 0.3
        )

        # Apply recency decay
        recent_count = sum(
            1 for c in contexts
            if (c.get("year") or c.get("source", {}).get("year", 0)) >= self.target_year - 5
        )
        recency_boost = 1.0 + 0.1 * min(recent_count, 5)

        return reading_value * recency_boost

    def _compute_production_value(self, contexts: list[dict], freq: dict) -> float:
        """Compute value for writing/translation"""
        production_value = 0.0
        for ctx in contexts:
            source = ctx.get("source", {})
            role = ctx.get("role") or source.get("role")
            year = ctx.get("year") or source.get("year", 0)

            if role in self.ROLE_VALUES:
                role_weight = self.ROLE_VALUES[role]
            else:
                role_weight = self.ROLE_VALUES.get("none", 0.2)

            # Recency decay (exponential)
            recency_weight = math.exp(-0.15 * (self.target_year - year))

            production_value += role_weight * recency_weight

        return production_value

    def _compute_discrimination_value(self, freq: dict) -> float:
        """Compute value for distinguishing confusable words"""
        role_counts = freq.get("by_role", {})

        answer_count = role_counts.get(AnnotationRole.CORRECT_ANSWER, 0)
        distractor_count = role_counts.get(AnnotationRole.DISTRACTOR, 0)

        # Words that appear as both answer AND distractor are high-value
        # (they are commonly confused)
        if answer_count > 0 and distractor_count > 0:
            # Geometric mean of both counts
            discrimination = math.sqrt(answer_count * distractor_count)
        else:
            discrimination = 0.0

        return discrimination

    def _compute_recency_value(self, contexts: list[dict], freq: dict) -> float:
        """Compute temporal relevance value"""
        years = freq.get("years", [])
        if not years:
            return 0.0

        # Filter to historical years
        historical_years = [y for y in years if y < self.target_year]
        if not historical_years:
            return 0.0

        # Exponentially weighted recency
        recency_sum = sum(
            math.exp(-0.2 * (self.target_year - y))
            for y in historical_years
            if y >= self.target_year - 10
        )

        # Bonus for new curriculum presence
        new_curriculum = [y for y in historical_years if y >= self.CURRICULUM_CUTOFF]
        curriculum_bonus = len(new_curriculum) * 0.3

        return recency_sum + curriculum_bonus

    def _compute_difficulty_match(self, level: int) -> float:
        """Compute how well difficulty matches target student"""
        if level == 0:
            return 0.5  # Unknown level

        # Sweet spot is L3-L5
        if 3 <= level <= 5:
            return 1.0
        elif level == 2 or level == 6:
            return 0.7
        else:
            return 0.4

    def _compute_effort_factor(self, level: int) -> float:
        """Learning effort factor (inverse of difficulty)"""
        if level == 0:
            return 1.0
        # L1 = 2.0, L6 = 0.67
        return 2.0 / (0.5 + 0.25 * level)

    def _estimate_recognition_gain(self, contexts: list[dict], freq: dict) -> float:
        """Estimate gain in recognition ability"""
        section_counts = freq.get("by_section", {})

        total_reading = (
            section_counts.get(SectionType.READING, 0) +
            section_counts.get(SectionType.CLOZE, 0) +
            section_counts.get(SectionType.DISCOURSE, 0)
        )

        return min(5.0, math.log1p(total_reading) * 1.5)

    def _estimate_production_gain(self, contexts: list[dict], freq: dict) -> float:
        """Estimate gain in production ability"""
        role_counts = freq.get("by_role", {})

        answer_count = role_counts.get(AnnotationRole.CORRECT_ANSWER, 0)
        keyword_count = role_counts.get(AnnotationRole.TESTED_KEYWORD, 0)
        # notable_phrase indicates exam makers flagged this phrase as important
        # It has recognition value and potential production value
        notable_count = role_counts.get("notable_phrase", 0)

        return min(5.0, (
            answer_count * 1.0 +
            keyword_count * 2.0 +
            notable_count * 0.5  # Lower than direct testing but still valuable
        ))

    def _analyze_senses(self, senses: list[dict]) -> dict:
        """Analyze sense-level coverage and risk"""
        if not senses:
            return {"coverage": 0.0, "untested_count": 0, "highest_risk": None}

        tested_senses = 0
        highest_risk_sense = None
        max_risk = 0.0

        for sense in senses:
            examples = sense.get("examples", [])
            if examples:
                tested_senses += 1
            else:
                # Untested sense = potential exam target
                # Risk based on definition complexity
                zh_def = sense.get("zh_def", "")
                en_def = sense.get("en_def", "")
                complexity = len(zh_def) + len(en_def)

                # More complex definitions often represent advanced usage
                risk = min(1.0, complexity / 100.0)

                if risk > max_risk:
                    max_risk = risk
                    highest_risk_sense = sense.get("sense_id")

        coverage = tested_senses / len(senses) if senses else 0.0
        untested = len(senses) - tested_senses

        return {
            "coverage": coverage,
            "untested_count": untested,
            "highest_risk": highest_risk_sense,
        }

    def _generate_interpretation(self, value: VocabValue, word_data: dict) -> str:
        """Generate human-readable interpretation"""
        parts = []

        if value.production.raw_value > 2.0:
            parts.append("高產出價值（常作為考題答案）")

        if value.discrimination.raw_value > 1.0:
            parts.append("易混淆詞彙（需特別區分）")

        if value.recency.raw_value > 2.0:
            parts.append("近年活躍")

        if value.untested_sense_count > 0:
            parts.append(f"有 {value.untested_sense_count} 個未被測試的義項")

        if 3 <= (value.level or 0) <= 5:
            parts.append("難度適中（L3-L5）")

        return "；".join(parts) if parts else "一般詞彙"

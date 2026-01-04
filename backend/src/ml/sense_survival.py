"""
Sense-level survival analysis for GSAT vocabulary prediction.

Key insight from IMPROVEMENT_PLAN.md:
- Words are not tested uniformly - specific SENSES are tested
- "address" example: 義項 "地址" rarely tested, 義項 "處理問題" frequently tested
- Sense-level granularity captures the true exam patterns

This module extends the basic survival analysis to work at sense level:
1. Track which senses have been tested (from WSD data)
2. Predict hazard for each sense independently
3. Identify "untested senses" as high-value targets
"""

import logging
import math
import pickle
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lifelines import CoxPHFitter

from ..models.exam import AnnotationRole

logger = logging.getLogger(__name__)


@dataclass
class SenseTestingHistory:
    """Testing history for a single sense"""
    sense_id: str
    sense_def_zh: str
    sense_def_en: str

    # Test counts
    total_examples: int = 0
    as_answer_count: int = 0
    as_distractor_count: int = 0

    # Year tracking
    years_tested: list[int] = field(default_factory=list)
    last_tested_year: int = 0

    # Computed hazard
    hazard: float = 0.0


@dataclass
class WordSenseAnalysis:
    """Complete sense-level analysis for a word"""
    lemma: str
    total_senses: int = 0

    # Sense-level details
    senses: list[SenseTestingHistory] = field(default_factory=list)

    # Aggregated metrics
    tested_sense_count: int = 0
    untested_sense_count: int = 0
    sense_coverage: float = 0.0

    # Highest risk sense (most likely to be tested next)
    highest_risk_sense_id: str | None = None
    highest_risk_hazard: float = 0.0

    # Entropy of sense testing distribution
    sense_entropy: float = 0.0

    # Word-level aggregated hazard
    word_hazard: float = 0.0


class SenseLevelSurvival:
    """
    Sense-level survival analysis model.

    Tracks testing "events" at the sense level rather than word level.
    """

    def __init__(
        self,
        penalizer: float = 0.1,
        min_samples: int = 50,
    ):
        self.penalizer = penalizer
        self.min_samples = min_samples

        self.model: CoxPHFitter | None = None
        self._feature_names: list[str] = []

    def _extract_sense_features(
        self,
        sense: dict,
        word_data: dict,
        target_year: int,
    ) -> dict[str, float]:
        """Extract features for a single sense"""
        from ..models.exam import ExamType

        examples = sense.get("examples", [])

        # Filter to historical examples from OFFICIAL exams only
        official_exam_types = {ExamType.GSAT, ExamType.GSAT_MAKEUP, ExamType.AST, ExamType.AST_MAKEUP}

        historical = []
        for ex in examples:
            source = ex.get("source", {})
            year = source.get("year", 0)
            exam_type = source.get("exam_type")
            # Include if year < target_year, but only count official exams for "tested"
            if year > 0 and year < target_year:
                historical.append(ex)

        # Basic counts
        total_examples = len(historical)

        # Role distribution - ONLY from official exams
        role_counts = defaultdict(int)
        years_tested = []

        for ex in historical:
            source = ex.get("source", {})
            role = source.get("role")
            year = source.get("year", 0)
            exam_type = source.get("exam_type")

            if role:
                role_counts[str(role)] += 1
            # CRITICAL: Only count official exam years as "tested"
            if year > 0 and exam_type in official_exam_types:
                years_tested.append(year)

        years_tested = sorted(set(years_tested))

        # Definition complexity (proxy for "advanced usage")
        zh_def = sense.get("zh_def", "")
        en_def = sense.get("en_def", "")
        def_length = len(zh_def) + len(en_def)

        # Features
        features = {
            "sense_example_count": float(total_examples),
            "sense_log_examples": math.log1p(total_examples),
            "sense_years_tested": float(len(years_tested)),
            "sense_recency": float(target_year - max(years_tested)) if years_tested else 20.0,
            "sense_def_complexity": min(1.0, def_length / 100.0),
        }

        # Word-level context features (from frequency.by_role)
        word_level = word_data.get("level", 0) or 0
        word_freq = word_data.get("frequency", {})
        by_role = word_freq.get("by_role", {})

        features["word_level"] = float(word_level)
        features["word_total_appearances"] = float(word_freq.get("total_appearances", 0))
        features["word_tested_count"] = float(word_freq.get("tested_count", 0))
        features["word_as_answer_count"] = float(by_role.get("correct_answer", 0))
        features["word_as_distractor_count"] = float(by_role.get("distractor", 0))

        return features

    def prepare_training_data(
        self,
        vocab_data: list[dict],
        target_year: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare sense-level training data for survival analysis.

        Each row is a (word, sense) pair with:
        - duration: years since sense was last tested
        - event: 1 if sense was tested before target_year, 0 if censored
        - features: sense + word features
        """
        from ..models.exam import ExamType

        official_exam_types = {ExamType.GSAT, ExamType.GSAT_MAKEUP, ExamType.AST, ExamType.AST_MAKEUP}

        X_list = []
        durations = []
        events = []

        for word_data in vocab_data:
            senses = word_data.get("senses", [])

            for sense in senses:
                examples = sense.get("examples", [])

                # Get test years before target - ONLY from official exams
                test_years = sorted([
                    ex.get("source", {}).get("year", 0)
                    for ex in examples
                    if ex.get("source", {}).get("year", 0) < target_year
                    and ex.get("source", {}).get("exam_type") in official_exam_types
                ])

                if len(test_years) >= 2:
                    # Use last completed interval
                    start_year = test_years[-2]
                    end_year = test_years[-1]
                    duration = end_year - start_year

                    features = self._extract_sense_features(sense, word_data, start_year)
                    X_list.append(list(features.values()))
                    durations.append(float(duration))
                    events.append(1)

                    self._feature_names = list(features.keys())

        if not X_list:
            return np.array([]), np.array([]), np.array([])

        return np.array(X_list), np.array(durations), np.array(events)

    def fit(
        self,
        vocab_data: list[dict],
        target_year: int,
    ) -> dict[str, Any]:
        """
        Fit the sense-level survival model.
        """
        X, durations, events = self.prepare_training_data(vocab_data, target_year)

        if len(X) < self.min_samples:
            logger.warning(f"Insufficient sense-level data: {len(X)} < {self.min_samples}")
            return {"fitted": False, "samples": len(X)}

        # Prepare DataFrame
        df = pd.DataFrame(X, columns=pd.Index(self._feature_names))
        df["duration"] = durations
        df["event"] = events

        # Clip duration to reasonable range
        df["duration"] = df["duration"].clip(lower=0.5, upper=20.0)

        # Fit Cox PH model
        self.model = CoxPHFitter(penalizer=self.penalizer)
        try:
            self.model.fit(df, duration_col="duration", event_col="event", show_progress=False)
            c_index = self.model.concordance_index_

            logger.info(f"Sense-level survival model fitted: C-index={c_index:.4f}, samples={len(X)}")

            return {
                "fitted": True,
                "samples": len(X),
                "c_index": c_index,
            }
        except Exception as e:
            logger.error(f"Sense-level survival fitting failed: {e}")
            return {"fitted": False, "error": str(e)}

    def predict_sense_hazard(
        self,
        sense: dict,
        word_data: dict,
        target_year: int,
    ) -> float:
        """
        Predict hazard for a single sense.

        Higher hazard = more likely to be tested soon.
        """
        if self.model is None:
            return 0.5  # Default neutral hazard

        features = self._extract_sense_features(sense, word_data, target_year)
        df = pd.DataFrame([list(features.values())], columns=pd.Index(self._feature_names))

        try:
            hazard = self.model.predict_partial_hazard(df).values[0]
            # Normalize to [0, 1] range using sigmoid-like transform
            return float(1.0 / (1.0 + np.exp(-hazard + 1)))
        except Exception:
            return 0.5

    def analyze_word_senses(
        self,
        word_data: dict,
        target_year: int,
    ) -> WordSenseAnalysis:
        """
        Comprehensive sense-level analysis for a word.
        """
        from ..models.exam import ExamType

        official_exam_types = {ExamType.GSAT, ExamType.GSAT_MAKEUP, ExamType.AST, ExamType.AST_MAKEUP}

        lemma = word_data.get("lemma", "")
        senses = word_data.get("senses", [])

        if not senses:
            return WordSenseAnalysis(lemma=lemma)

        analysis = WordSenseAnalysis(
            lemma=lemma,
            total_senses=len(senses),
        )

        sense_histories = []
        hazards = []

        for sense in senses:
            sense_id = sense.get("sense_id", "")
            examples = sense.get("examples", [])

            # Get testing history - all examples before target_year
            historical = [
                ex for ex in examples
                if ex.get("source", {}).get("year", 0) < target_year
            ]

            # Count roles - from official exams only
            as_answer = sum(
                1 for ex in historical
                if ex.get("source", {}).get("role") == AnnotationRole.CORRECT_ANSWER.value
                and ex.get("source", {}).get("exam_type") in official_exam_types
            )
            as_distractor = sum(
                1 for ex in historical
                if ex.get("source", {}).get("role") == AnnotationRole.DISTRACTOR.value
                and ex.get("source", {}).get("exam_type") in official_exam_types
            )

            # CRITICAL: Only count official exam years as "tested"
            years = sorted([
                ex.get("source", {}).get("year", 0)
                for ex in historical
                if ex.get("source", {}).get("year", 0) > 0
                and ex.get("source", {}).get("exam_type") in official_exam_types
            ])

            # Predict hazard
            hazard = self.predict_sense_hazard(sense, word_data, target_year)

            history = SenseTestingHistory(
                sense_id=sense_id,
                sense_def_zh=sense.get("zh_def", ""),
                sense_def_en=sense.get("en_def", ""),
                total_examples=len(historical),
                as_answer_count=as_answer,
                as_distractor_count=as_distractor,
                years_tested=years,
                last_tested_year=max(years) if years else 0,
                hazard=hazard,
            )

            sense_histories.append(history)
            hazards.append(hazard)

        analysis.senses = sense_histories

        # Aggregated metrics - based on official exam testing
        tested_senses = [s for s in sense_histories if s.years_tested]  # Has official test years
        untested_senses = [s for s in sense_histories if not s.years_tested]

        analysis.tested_sense_count = len(tested_senses)
        analysis.untested_sense_count = len(untested_senses)
        analysis.sense_coverage = len(tested_senses) / len(senses) if senses else 0.0

        # Highest risk sense
        if hazards:
            max_idx = np.argmax(hazards)
            analysis.highest_risk_sense_id = sense_histories[max_idx].sense_id
            analysis.highest_risk_hazard = hazards[max_idx]

        # Sense entropy (diversity of testing)
        if tested_senses:
            total_examples = sum(s.total_examples for s in tested_senses)
            if total_examples > 0:
                probs = [s.total_examples / total_examples for s in tested_senses]
                analysis.sense_entropy = -sum(p * math.log(p) for p in probs if p > 0)

        # Word-level hazard (max of sense hazards, with untested sense bonus)
        if hazards:
            analysis.word_hazard = max(hazards)

            # Bonus for having untested senses (potential exam targets)
            if untested_senses:
                untested_bonus = 0.1 * len(untested_senses)
                analysis.word_hazard = min(1.0, analysis.word_hazard + untested_bonus)

        return analysis

    def extract_features(
        self,
        word_data: dict,
        target_year: int,
    ) -> dict[str, float]:
        """
        Extract sense-level features for ML pipeline integration.
        """
        analysis = self.analyze_word_senses(word_data, target_year)

        return {
            "sense_total_count": float(analysis.total_senses),
            "sense_tested_count": float(analysis.tested_sense_count),
            "sense_untested_count": float(analysis.untested_sense_count),
            "sense_coverage": analysis.sense_coverage,
            "sense_entropy": analysis.sense_entropy,
            "sense_max_hazard": analysis.highest_risk_hazard,
            "sense_word_hazard": analysis.word_hazard,
        }

    def save(self, path: Path):
        """Save model to disk"""
        data = {
            "model": self.model,
            "feature_names": self._feature_names,
            "penalizer": self.penalizer,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "SenseLevelSurvival":
        """Load model from disk"""
        with open(path, "rb") as f:
            data = pickle.load(f)

        obj = cls(penalizer=data["penalizer"])
        obj.model = data["model"]
        obj._feature_names = data["feature_names"]

        return obj


# Feature names for integration
SENSE_SURVIVAL_FEATURE_NAMES = [
    "sense_total_count",
    "sense_tested_count",
    "sense_untested_count",
    "sense_coverage",
    "sense_entropy",
    "sense_max_hazard",
    "sense_word_hazard",
]

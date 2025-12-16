"""
Feature extraction for GSAT vocabulary importance prediction.

Extracts linguistic, temporal, and contextual features from vocabulary data.
Supports multiple target modes:
- "appeared": Word appeared anywhere in the exam (passage, answer, etc.)
- "tested": Word was specifically tested (answer, keyword, or distractor)
- "active_tested": Word was answer or keyword only (not distractor)
- "answer_only": Word was the correct answer (strictest)
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .weights import (
    CURRICULUM_CUTOFF_YEAR,
    MAX_DISTRACTOR_PARTNER_CAP,
    RECENCY_WINDOW_YEARS,
    TRIAL_YEARS,
)

TESTED_ROLES = {"correct_answer", "tested_keyword", "distractor"}
ACTIVE_TESTED_ROLES = {"correct_answer", "tested_keyword"}
ANSWER_ONLY_ROLES = {"correct_answer"}

COMMON_PREFIXES = {
    "un",
    "re",
    "in",
    "im",
    "ir",
    "il",
    "dis",
    "en",
    "em",
    "non",
    "pre",
    "pro",
    "anti",
    "de",
    "fore",
    "inter",
    "mid",
    "mis",
    "over",
    "semi",
    "sub",
    "super",
    "trans",
    "under",
    "ex",
    "extra",
    "infra",
    "intra",
    "macro",
    "micro",
    "mega",
    "mini",
    "multi",
    "neo",
    "omni",
    "out",
    "poly",
    "post",
    "pseudo",
    "retro",
    "self",
    "tele",
    "tri",
    "ultra",
    "uni",
    "bi",
}

COMMON_SUFFIXES = {
    "able",
    "ible",
    "al",
    "ial",
    "ed",
    "en",
    "er",
    "or",
    "est",
    "ful",
    "ic",
    "ing",
    "ion",
    "tion",
    "ation",
    "ition",
    "ity",
    "ty",
    "ive",
    "ative",
    "itive",
    "less",
    "ly",
    "ment",
    "ness",
    "ous",
    "eous",
    "ious",
    "es",
    "s",
    "y",
    "ize",
    "ise",
    "ify",
    "ate",
    "ish",
    "ward",
    "wise",
    "dom",
    "hood",
    "ship",
    "ism",
    "ist",
    "ery",
    "ary",
    "ory",
}

FEATURE_NAMES = [
    # Basic occurrence features
    "total_occurrences",
    "log_occurrences",
    "tested_count",
    "active_tested_count",
    "year_spread",
    "tested_year_spread",
    "normalized_year_spread",
    # Official wordlist features
    "in_official",
    "level",
    "level_squared",
    # Linguistic features
    "word_length",
    "syllable_count",
    "has_prefix",
    "has_suffix",
    "wordnet_senses",
    "log_wordnet_senses",
    # Distractor analysis features (separated)
    "distractor_appearances",
    "distractor_partner_count",
    "correct_answer_appearances",
    "distractor_to_answer_ratio",
    "confusability_score",
    "answer_vs_distractor_balance",
    # Temporal features
    "recency",
    "recency_squared",
    "first_appearance_age",
    "appearance_density",
    "tested_density",
    "last_tested_gap",
    # Curriculum-related features
    "pre_curriculum_appearances",
    "post_curriculum_appearances",
    "pre_curriculum_tested",
    "post_curriculum_tested",
    "trial_period_appearances",
    "trial_period_tested",
    "curriculum_transition_ratio",
    "post_curriculum_year_spread",
    # Role distribution features
    "role_correct_answer",
    "role_tested_keyword",
    "role_distractor",
    "role_none",
    "role_notable_phrase",
    "role_notable_pattern",
    "tested_role_ratio",
    "answer_to_distractor_ratio",
    # Section distribution features
    "section_vocabulary",
    "section_cloze",
    "section_reading",
    "section_translation",
    "section_structure",
    "section_discourse",
    "section_mixed",
    "high_weight_section_ratio",
    # Exam type features
    "exam_gsat_ratio",
    "exam_gsat_ref_count",
    "exam_gsat_trial_count",
    "gsat_only_appearances",
    # POS features
    "pos_noun",
    "pos_verb",
    "pos_adj",
    "pos_adv",
    "pos_count",
    # Trend features
    "recent_trend",
    "tested_trend",
    "consistency_score",
    "testing_regularity",
    # Cooling off pattern (words tested recently may be avoided)
    "years_since_last_tested",
    "times_tested_in_window",
    "cooling_off_indicator",
    # Essay topic features (NEW)
    "in_essay_suggested",
    "essay_topic_count",
    "essay_recency",
]


@dataclass
class WordFeatureData:
    lemma: str
    level: int | None = None
    in_official: bool = False
    pos_list: list[str] = field(default_factory=list)

    years_appeared: set[int] = field(default_factory=set)
    years_tested: set[int] = field(default_factory=set)
    years_actively_tested: set[int] = field(default_factory=set)
    years_answer_only: set[int] = field(default_factory=set)
    role_by_year: dict[int, dict[str, int]] = field(default_factory=dict)
    section_by_year: dict[int, dict[str, int]] = field(default_factory=dict)
    exam_types_by_year: dict[int, dict[str, int]] = field(default_factory=dict)

    word_length: int = 0
    syllable_count: int = 0
    has_prefix: bool = False
    has_suffix: bool = False
    wordnet_sense_count: int = 0

    distractor_appearances: int = 0
    distractor_partners: set[str] = field(default_factory=set)
    correct_answer_appearances: int = 0

    confusable_words: set[str] = field(default_factory=set)

    essay_years: set[int] = field(default_factory=set)
    essay_count: int = 0


def count_syllables(word: str) -> int:
    word = word.lower()
    if len(word) <= 3:
        return 1

    vowels = "aeiouy"
    count = 0
    prev_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    if word.endswith("e") and count > 1:
        count -= 1
    if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
        count += 1

    return max(1, count)


def has_common_prefix(word: str) -> bool:
    word_lower = word.lower()
    return any(word_lower.startswith(prefix) for prefix in COMMON_PREFIXES)


def has_common_suffix(word: str) -> bool:
    word_lower = word.lower()
    return any(word_lower.endswith(suffix) for suffix in COMMON_SUFFIXES)


def get_wordnet_sense_count(word: str) -> int:
    try:
        from nltk.corpus import wordnet

        synsets = wordnet.synsets(word)
        return len(synsets)
    except Exception:
        return 1


class FeatureExtractor:
    def __init__(self, current_year: int = 114):
        self.current_year = current_year
        self.distractor_partner_index: dict[str, set[str]] = {}
        self.correct_answer_index: dict[str, int] = {}
        self.essay_word_index: dict[str, list[int]] = {}

    def build_distractor_index(self, distractor_groups: list[dict]) -> None:
        self.distractor_partner_index = defaultdict(set)
        self.correct_answer_index = defaultdict(int)
        self.distractor_count_index = defaultdict(int)
        self.confusable_pairs: dict[str, set[str]] = defaultdict(set)

        for group in distractor_groups:
            correct = group.get("correct_answer", "").lower()
            distractors = [d.lower() for d in group.get("distractors", [])]

            self.correct_answer_index[correct] += 1

            for d in distractors:
                self.distractor_count_index[d] += 1
                self.confusable_pairs[d].add(correct)
                self.confusable_pairs[correct].add(d)

            all_words = [correct] + distractors
            for word in all_words:
                for other in all_words:
                    if other != word:
                        self.distractor_partner_index[word].add(other)

    def build_essay_index(self, essay_topics: list[dict]) -> None:
        self.essay_word_index = defaultdict(list)

        for topic in essay_topics:
            year = topic.get("source", {}).get("year", 0)
            suggested_words = topic.get("suggested_words", [])

            for word in suggested_words:
                word_lower = word.lower()
                self.essay_word_index[word_lower].append(year)

    def extract_word_data(self, entry: dict[str, Any]) -> WordFeatureData:
        lemma = entry["lemma"]
        occurrences = entry.get("occurrences", [])

        wf = WordFeatureData(
            lemma=lemma,
            level=entry.get("level"),
            in_official=entry.get("in_official_list", False),
            pos_list=entry.get("pos", []),
        )

        wf.word_length = len(lemma)
        wf.syllable_count = count_syllables(lemma)
        wf.has_prefix = has_common_prefix(lemma)
        wf.has_suffix = has_common_suffix(lemma)
        wf.wordnet_sense_count = get_wordnet_sense_count(lemma)

        for occ in occurrences:
            source = occ.get("source", {})
            year = source.get("year", 0)
            role = occ.get("role") or "none"
            section = source.get("section_type", "mixed")
            exam_type = source.get("exam_type", "gsat")

            if year > 0:
                wf.years_appeared.add(year)

                if year not in wf.role_by_year:
                    wf.role_by_year[year] = defaultdict(int)
                wf.role_by_year[year][role] += 1

                if year not in wf.section_by_year:
                    wf.section_by_year[year] = defaultdict(int)
                wf.section_by_year[year][section] += 1

                if year not in wf.exam_types_by_year:
                    wf.exam_types_by_year[year] = defaultdict(int)
                wf.exam_types_by_year[year][exam_type] += 1

                if role in TESTED_ROLES:
                    wf.years_tested.add(year)
                if role in ACTIVE_TESTED_ROLES:
                    wf.years_actively_tested.add(year)
                if role in ANSWER_ONLY_ROLES:
                    wf.years_answer_only.add(year)

        lemma_lower = lemma.lower()
        wf.distractor_appearances = self.distractor_count_index.get(lemma_lower, 0)
        wf.distractor_partners = self.distractor_partner_index.get(lemma_lower, set())
        wf.correct_answer_appearances = self.correct_answer_index.get(lemma_lower, 0)
        wf.confusable_words = self.confusable_pairs.get(lemma_lower, set())

        essay_years = self.essay_word_index.get(lemma_lower, [])
        wf.essay_years = set(essay_years)
        wf.essay_count = len(essay_years)

        return wf

    def get_target_label(
        self,
        wf: WordFeatureData,
        target_year: int,
        target_mode: str = "tested",
    ) -> int:
        if target_mode == "appeared":
            return 1 if target_year in wf.years_appeared else 0
        elif target_mode == "tested":
            return 1 if target_year in wf.years_tested else 0
        elif target_mode == "active_tested":
            return 1 if target_year in wf.years_actively_tested else 0
        elif target_mode == "answer_only":
            return 1 if target_year in wf.years_answer_only else 0
        else:
            raise ValueError(f"Unknown target_mode: {target_mode}")

    def extract_feature_vector(
        self,
        wf: WordFeatureData,
        target_year: int | None = None,
        lookback_years: int = 15,
    ) -> list[float] | None:
        if target_year is None:
            target_year = self.current_year

        cutoff_year = target_year
        min_year = max(83, cutoff_year - lookback_years)

        years_before = {y for y in wf.years_appeared if min_year <= y < cutoff_year}
        if not years_before:
            return None

        years_tested_before = {y for y in wf.years_tested if min_year <= y < cutoff_year}

        total_occ = sum(
            sum(roles.values())
            for y, roles in wf.role_by_year.items()
            if min_year <= y < cutoff_year
        )

        tested_count = sum(
            wf.role_by_year.get(y, {}).get("correct_answer", 0)
            + wf.role_by_year.get(y, {}).get("tested_keyword", 0)
            + wf.role_by_year.get(y, {}).get("distractor", 0)
            for y in years_before
        )

        active_tested_count = sum(
            wf.role_by_year.get(y, {}).get("correct_answer", 0)
            + wf.role_by_year.get(y, {}).get("tested_keyword", 0)
            for y in years_before
        )

        year_spread = len(years_before)
        tested_year_spread = len(years_tested_before)
        level = wf.level if wf.level is not None else 4

        total_possible_years = cutoff_year - min_year
        normalized_year_spread = year_spread / max(1, total_possible_years)

        recency = cutoff_year - max(years_before)
        first_appearance_age = cutoff_year - min(years_before)
        appearance_density = year_spread / max(1, first_appearance_age)
        tested_density = tested_year_spread / max(1, first_appearance_age)

        last_tested_year = max(years_tested_before) if years_tested_before else min_year
        last_tested_gap = cutoff_year - last_tested_year

        role_counts: dict[str, int] = defaultdict(int)
        section_counts: dict[str, int] = defaultdict(int)
        gsat_count = 0
        gsat_ref_count = 0
        gsat_trial_count = 0
        gsat_only_count = 0
        total_exam_count = 0

        for y in years_before:
            for role, count in wf.role_by_year.get(y, {}).items():
                role_counts[role] += count
            for section, count in wf.section_by_year.get(y, {}).items():
                section_counts[section] += count
            for exam_type, count in wf.exam_types_by_year.get(y, {}).items():
                total_exam_count += count
                if exam_type.startswith("gsat"):
                    gsat_count += count
                    if exam_type == "gsat":
                        gsat_only_count += count
                if exam_type == "gsat_ref":
                    gsat_ref_count += count
                if exam_type == "gsat_trial":
                    gsat_trial_count += count

        gsat_ratio = gsat_count / max(1, total_exam_count)

        total_role_count = sum(role_counts.values())
        tested_role_count = (
            role_counts.get("correct_answer", 0)
            + role_counts.get("tested_keyword", 0)
            + role_counts.get("distractor", 0)
        )
        tested_role_ratio = tested_role_count / max(1, total_role_count)

        answer_count = role_counts.get("correct_answer", 0) + role_counts.get("tested_keyword", 0)
        distractor_count = role_counts.get("distractor", 0)
        answer_to_distractor_ratio = (
            answer_count / max(1, distractor_count) if distractor_count > 0 else answer_count
        )

        answer_vs_distractor_balance = (answer_count - distractor_count) / max(
            1, answer_count + distractor_count
        )

        high_weight_sections = (
            section_counts.get("vocabulary", 0)
            + section_counts.get("structure", 0)
            + section_counts.get("translation", 0)
        )
        total_section_count = sum(section_counts.values())
        high_weight_section_ratio = high_weight_sections / max(1, total_section_count)

        recent_appearances = sum(1 for y in years_before if cutoff_year - y <= RECENCY_WINDOW_YEARS)
        older_appearances = sum(1 for y in years_before if cutoff_year - y > RECENCY_WINDOW_YEARS)
        recent_trend = (recent_appearances - older_appearances) / max(1, year_spread)

        recent_tested = sum(
            1 for y in years_tested_before if cutoff_year - y <= RECENCY_WINDOW_YEARS
        )
        older_tested = sum(1 for y in years_tested_before if cutoff_year - y > RECENCY_WINDOW_YEARS)
        tested_trend = (
            (recent_tested - older_tested) / max(1, tested_year_spread)
            if tested_year_spread > 0
            else 0
        )

        years_list = sorted(years_before)
        if len(years_list) >= 2:
            gaps = [years_list[i + 1] - years_list[i] for i in range(len(years_list) - 1)]
            consistency_score = 1.0 / (1.0 + np.std(gaps)) if gaps else 1.0
        else:
            consistency_score = 0.5

        tested_years_list = sorted(years_tested_before)
        if len(tested_years_list) >= 2:
            tested_gaps = [
                tested_years_list[i + 1] - tested_years_list[i]
                for i in range(len(tested_years_list) - 1)
            ]
            testing_regularity = 1.0 / (1.0 + np.std(tested_gaps)) if tested_gaps else 1.0
        else:
            testing_regularity = 0.5 if tested_year_spread > 0 else 0.0

        pre_curriculum_app = sum(
            sum(roles.values())
            for y, roles in wf.role_by_year.items()
            if min_year <= y < min(cutoff_year, CURRICULUM_CUTOFF_YEAR)
        )
        post_curriculum_app = sum(
            sum(roles.values())
            for y, roles in wf.role_by_year.items()
            if CURRICULUM_CUTOFF_YEAR <= y < cutoff_year
        )
        pre_curriculum_tested = sum(
            wf.role_by_year.get(y, {}).get("correct_answer", 0)
            + wf.role_by_year.get(y, {}).get("tested_keyword", 0)
            for y in years_before
            if y < CURRICULUM_CUTOFF_YEAR
        )
        post_curriculum_tested = sum(
            wf.role_by_year.get(y, {}).get("correct_answer", 0)
            + wf.role_by_year.get(y, {}).get("tested_keyword", 0)
            for y in years_before
            if y >= CURRICULUM_CUTOFF_YEAR
        )

        curriculum_transition_ratio = (
            post_curriculum_app / max(1, pre_curriculum_app)
            if pre_curriculum_app > 0
            else float(post_curriculum_app)
        )

        post_curriculum_years = {y for y in years_before if y >= CURRICULUM_CUTOFF_YEAR}
        post_curriculum_year_spread = len(post_curriculum_years)

        trial_period_app = sum(
            sum(roles.values())
            for y, roles in wf.role_by_year.items()
            if y in TRIAL_YEARS and y < cutoff_year
        )
        trial_period_tested = sum(
            wf.role_by_year.get(y, {}).get("correct_answer", 0)
            + wf.role_by_year.get(y, {}).get("tested_keyword", 0)
            for y in years_before
            if y in TRIAL_YEARS
        )

        distractor_to_answer = (
            wf.distractor_appearances / max(1, wf.correct_answer_appearances)
            if wf.correct_answer_appearances > 0
            else float(wf.distractor_appearances)
        )
        confusability_score = len(wf.confusable_words) / max(
            1, wf.distractor_appearances + wf.correct_answer_appearances
        )

        years_since_last_tested = (
            cutoff_year - last_tested_year if years_tested_before else lookback_years
        )
        times_tested_in_window = sum(1 for y in years_tested_before if cutoff_year - y <= 3)
        cooling_off_indicator = (
            1.0 if (times_tested_in_window >= 2 and years_since_last_tested <= 1) else 0.0
        )

        pos_count = len(wf.pos_list)

        essay_years_before = {y for y in wf.essay_years if y < cutoff_year}
        in_essay_suggested = 1.0 if essay_years_before else 0.0
        essay_topic_count = len(essay_years_before)
        essay_recency = (
            (cutoff_year - max(essay_years_before)) if essay_years_before else lookback_years
        )

        features = [
            # Basic occurrence features
            float(total_occ),
            math.log1p(total_occ),
            float(tested_count),
            float(active_tested_count),
            float(year_spread),
            float(tested_year_spread),
            float(normalized_year_spread),
            # Official wordlist features
            1.0 if wf.in_official else 0.0,
            float(level),
            float(level**2),
            # Linguistic features
            float(wf.word_length),
            float(wf.syllable_count),
            1.0 if wf.has_prefix else 0.0,
            1.0 if wf.has_suffix else 0.0,
            float(wf.wordnet_sense_count),
            math.log1p(wf.wordnet_sense_count),
            # Distractor analysis features (separated)
            float(wf.distractor_appearances),
            float(min(len(wf.distractor_partners), MAX_DISTRACTOR_PARTNER_CAP)),
            float(wf.correct_answer_appearances),
            float(distractor_to_answer),
            float(confusability_score),
            float(answer_vs_distractor_balance),
            # Temporal features
            float(recency),
            float(recency**2),
            float(first_appearance_age),
            float(appearance_density),
            float(tested_density),
            float(last_tested_gap),
            # Curriculum-related features
            float(pre_curriculum_app),
            float(post_curriculum_app),
            float(pre_curriculum_tested),
            float(post_curriculum_tested),
            float(trial_period_app),
            float(trial_period_tested),
            float(curriculum_transition_ratio),
            float(post_curriculum_year_spread),
            # Role distribution features
            float(role_counts.get("correct_answer", 0)),
            float(role_counts.get("tested_keyword", 0)),
            float(role_counts.get("distractor", 0)),
            float(role_counts.get("none", 0)),
            float(role_counts.get("notable_phrase", 0)),
            float(role_counts.get("notable_pattern", 0)),
            float(tested_role_ratio),
            float(answer_to_distractor_ratio),
            # Section distribution features
            float(section_counts.get("vocabulary", 0)),
            float(section_counts.get("cloze", 0)),
            float(section_counts.get("reading", 0)),
            float(section_counts.get("translation", 0)),
            float(section_counts.get("structure", 0)),
            float(section_counts.get("discourse", 0)),
            float(section_counts.get("mixed", 0)),
            float(high_weight_section_ratio),
            # Exam type features
            float(gsat_ratio),
            float(gsat_ref_count),
            float(gsat_trial_count),
            float(gsat_only_count),
            # POS features
            1.0 if "NOUN" in wf.pos_list else 0.0,
            1.0 if "VERB" in wf.pos_list else 0.0,
            1.0 if "ADJ" in wf.pos_list else 0.0,
            1.0 if "ADV" in wf.pos_list else 0.0,
            float(pos_count),
            # Trend features
            float(recent_trend),
            float(tested_trend),
            float(consistency_score),
            float(testing_regularity),
            # Cooling off pattern
            float(years_since_last_tested),
            float(times_tested_in_window),
            float(cooling_off_indicator),
            # Essay topic features (NEW)
            float(in_essay_suggested),
            float(essay_topic_count),
            float(essay_recency),
        ]

        return features


def extract_features_for_word(
    entry: dict[str, Any],
    distractor_groups: list[dict],
    essay_topics: list[dict] | None = None,
    current_year: int = 114,
) -> list[float] | None:
    extractor = FeatureExtractor(current_year=current_year)
    extractor.build_distractor_index(distractor_groups)
    if essay_topics:
        extractor.build_essay_index(essay_topics)

    word_data = extractor.extract_word_data(entry)
    return extractor.extract_feature_vector(word_data)


def get_feature_names() -> list[str]:
    return FEATURE_NAMES.copy()

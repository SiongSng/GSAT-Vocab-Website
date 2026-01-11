"""
Feature extraction for GSAT vocabulary importance prediction.

Extracts linguistic, temporal, contextual, and Semantic (WSD) features.
Supports multiple target modes:
- "appeared": Word appeared anywhere in the exam (passage, answer, etc.)
- "tested": Word was a question option or key part of the question.
- "active_tested": Word was the correct answer or a tested keyword.
- "answer_only": Word was the correct answer.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..models.exam import AnnotationRole, ExamType, SectionType, SentenceRole

# GSAT & AST Year Ranges
# GSAT: 83-114
# AST: 91-114
GSAT_RANGE = range(83, 116)
AST_RANGE = range(91, 116)

# Config
RECENCY_WINDOW_YEARS = 10
MAX_DISTRACTOR_PARTNER_CAP = 10
TRIAL_YEARS = {110, 111}  # Known trial exam years

REFERENCE_EXAM_TYPES = {ExamType.GSAT_REF, ExamType.GSAT_TRIAL}
OFFICIAL_EXAM_TYPES = {
    ExamType.GSAT,
    ExamType.GSAT_MAKEUP,
    ExamType.AST,
    ExamType.AST_MAKEUP,
}

# Target Role Groups
TESTED_ROLES = {
    AnnotationRole.CORRECT_ANSWER,
    AnnotationRole.TESTED_KEYWORD,
    AnnotationRole.DISTRACTOR,
}
ACTIVE_TESTED_ROLES = {AnnotationRole.CORRECT_ANSWER, AnnotationRole.TESTED_KEYWORD}
ANSWER_ONLY_ROLES = {AnnotationRole.CORRECT_ANSWER}

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
    "out",
    "co",
    "ex",
    "auto",
    "bio",
    "tele",
    "micro",
    "macro",
    "multi",
    "poly",
    "uni",
    "tri",
    "bi",
    "quad",
    "oct",
    "dec",
    "cent",
    "milli",
    "kilo",
    "mega",
    "giga",
    "tera",
    "nano",
    "pico",
    "femto",
    "atto",
    "zepto",
    "yocto",
}

COMMON_SUFFIXES = {
    "tion",
    "sion",
    "ment",
    "ance",
    "ence",
    "ant",
    "ent",
    "er",
    "or",
    "ar",
    "ist",
    "ism",
    "ity",
    "ty",
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
    "ery",
    "ary",
    "ory",
    "al",
    "ic",
    "ive",
    "ful",
    "less",
    "able",
    "ible",
    "ly",
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
    "official_level",
    # Linguistic features
    "length",
    "syllables",
    "has_common_prefix",
    "has_common_suffix",
    "wn_synset_count",
    "wn_avg_hypernyms",
    "wn_avg_hyponyms",
    "wn_avg_depth",
    "wn_domain_diversity",
    "synonym_count",
    "antonym_count",
    # Distractor analysis
    "distractor_count",
    "correct_answer_count",
    "answer_to_option_ratio",
    # Temporal recency
    "recency_score",
    "years_since_last_tested",
    "raw_appearance_spread",
    "normalized_appearance_spread",
    # Curriculum relevance
    "recent_5y_count",
    "appeared_in_recent_5y",
    # Detailed distribution
    "role_correct_answer",
    "role_distractor",
    "role_question_prompt",
    "role_passage_word",
    "role_option",
    "role_none",
    "role_correct_ratio",
    "role_distractor_ratio",
    # Section distribution
    "section_vocabulary",
    "section_cloze",
    "section_reading",
    "section_translation",
    "section_essay",  # Replaces structure/discourse/mixed aggregation
    "exam_gsat_count",
    "exam_ast_count",
    "exam_trial_count",
    "exam_gsat_ratio",
    "exam_ast_ratio",
    # Advanced Temporal
    "frequency_trend",
    "avg_gap_years",
    "gap_deviation",  # (last_gap - avg_gap)
    "consistency_variance",
    # Essay
    "is_essay_topic",
    "is_essay_suggested",
    # High Weight
    "high_weight_section_ratio",
    # Tested Only
    "tested_years_count",
    "tested_trend",
    "tested_year_spread_val",
    # Age
    "corpus_age",
    # Regularity
    "testing_regularity",
    # Phase 3
    "sense_count_proxy",
    "tested_sense_diversity",
    "tested_sense_ratio",
    "primary_sense_dominance_proxy",
    "role_cloze_ratio",
    "role_passage_ratio",
    "role_option_ratio",
    "cloze_as_answer_ratio",
    "ref_exam_count",
    "ref_recency",
    "trial_exam_count",
    "ref_trial_signal_gap",
    # Phase 9
    "wsd_entropy",
    "wsd_max_ratio",
    "wsd_sense_count",
    "wsd_active_sense_count",
    "wsd_question_prompt_ratio",
    "wsd_recency_spread",
    "survival_hazard",
    "synonym_tested_freq",
    "level_difficulty_match",
]


import nltk
from nltk.corpus import wordnet as wn


def get_wordnet_features(lemma: str) -> dict:
    """Extract semantic network features from WordNet."""
    try:
        synsets = wn.synsets(lemma)
        if not synsets:
            return {
                "synset_count": 0,
                "avg_hypernyms": 0.0,
                "avg_hyponyms": 0.0,
                "avg_depth": 0.0,
                "domain_diversity": 0,
            }

        hyper_counts = []
        hypo_counts = []
        depths = []
        lexnames = set()

        for s in synsets:
            hyper_counts.append(len(s.hypernyms()))
            hypo_counts.append(len(s.hyponyms()))
            depths.append(s.min_depth())
            lexnames.add(s.lexname())

        return {
            "synset_count": len(synsets),
            "avg_hypernyms": sum(hyper_counts) / len(synsets),
            "avg_hyponyms": sum(hypo_counts) / len(synsets),
            "avg_depth": sum(depths) / len(synsets),
            "domain_diversity": len(lexnames),
        }
    except:
        return {
            "synset_count": 0,
            "avg_hypernyms": 0.0,
            "avg_hyponyms": 0.0,
            "avg_depth": 0.0,
            "domain_diversity": 0,
        }


@dataclass
class WordFeatureData:
    lemma: str
    level: int = 0
    in_official: bool = False

    # Linguistic features
    length: int = 0
    syllables: int = 0
    has_common_prefix: bool = False
    has_common_suffix: bool = False

    # WordNet Features
    wn_synset_count: int = 0
    wn_avg_hypernyms: float = 0.0
    wn_avg_hyponyms: float = 0.0
    wn_avg_depth: float = 0.0
    wn_domain_diversity: int = 0

    # Raw context history
    contexts_raw: list[dict] = field(default_factory=list)

    # WSD Semantic data (pre-processed)
    # Map Year -> SenseIndex -> Count
    wsd_year_sense_map: dict[int, dict[int, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    # Map SenseIndex -> Role -> Count
    wsd_sense_role_map: dict[int, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    # Relations
    synonym_count: int = 0
    antonym_count: int = 0

    # Derived Properties (Used for labels and survival analysis)
    years_appeared: list[int] = field(default_factory=list)
    years_tested: list[int] = field(default_factory=list)
    essay_years: list[int] = field(default_factory=list)


def count_syllables(word: str) -> int:
    return max(1, len([c for c in word if c.lower() in "aeiouy"]))


def has_common_prefix(word: str) -> bool:
    return any(word.lower().startswith(p) for p in COMMON_PREFIXES)


def has_common_suffix(word: str) -> bool:
    return any(word.lower().endswith(s) for s in COMMON_SUFFIXES)


class FeatureExtractor:
    def __init__(self, current_year: int = 114):
        self.current_year = current_year

    def get_target_label(
        self, word_data: WordFeatureData, target_year: int, target_mode: str
    ) -> int:
        """Calculate the ground truth label for a word in a specific year and mode."""
        # For labeling, we look ONLY at the target_year's GSAT/AST official exams
        for occ in word_data.contexts_raw:
            if occ.get("year") != target_year:
                continue

            # We only count it as "ground truth" if it appears in the official exams of that year
            if occ.get("exam_type") not in [ExamType.GSAT, ExamType.AST]:
                continue

            role = occ.get("role")
            if target_mode == "appeared":
                return 1
            elif target_mode == "tested":
                if role in [
                    AnnotationRole.CORRECT_ANSWER,
                    AnnotationRole.TESTED_KEYWORD,
                    AnnotationRole.DISTRACTOR,
                ]:
                    return 1
            elif target_mode == "active_tested":
                if role in [AnnotationRole.CORRECT_ANSWER, AnnotationRole.TESTED_KEYWORD]:
                    return 1
            elif target_mode == "answer_only":
                if role == AnnotationRole.CORRECT_ANSWER:
                    return 1
        return 0

    def extract_word_data(self, entry: Any) -> WordFeatureData:
        """Extract features from vocab.json WordEntry.

        vocab.json structure:
        - lemma, pos, level, in_official_list
        - frequency: {total_appearances, tested_count, years, by_role, by_section, by_exam_type}
        - senses: [{sense_id, examples: [{text, source: {year, exam_type, section_type, role}}]}]
        - synonyms, antonyms
        """
        if isinstance(entry, dict):
            lemma = entry.get("lemma") or entry.get("word") or ""
        else:
            lemma = getattr(entry, "lemma", "")

        wf = WordFeatureData(lemma=lemma)

        # 1. Basic Properties
        if isinstance(entry, dict):
            wf.level = int(entry.get("level") or 0)
            wf.in_official = entry.get("in_official_list", False)
        else:
            wf.level = getattr(entry, "level", 0) or 0
            wf.in_official = getattr(entry, "in_official_list", False)

        wf.length = len(lemma)
        wf.syllables = count_syllables(lemma)
        wf.has_common_prefix = has_common_prefix(lemma)
        wf.has_common_suffix = has_common_suffix(lemma)

        wn_feats = get_wordnet_features(lemma)
        wf.wn_synset_count = wn_feats["synset_count"]
        wf.wn_avg_hypernyms = wn_feats["avg_hypernyms"]
        wf.wn_avg_hyponyms = wn_feats["avg_hyponyms"]
        wf.wn_avg_depth = wn_feats["avg_depth"]
        wf.wn_domain_diversity = wn_feats["domain_diversity"]

        # 2. Extract contexts from senses[].examples[] (vocab.json structure)
        # Each example has: text, source: {year, exam_type, section_type, role, sentence_role}
        senses = (
            entry.get("senses", []) if isinstance(entry, dict) else getattr(entry, "senses", [])
        )

        for s_idx, sense in enumerate(senses):
            if isinstance(sense, dict):
                examples = sense.get("examples", [])
            else:
                examples = getattr(sense, "examples", [])

            for ex in examples:
                if isinstance(ex, dict):
                    source = ex.get("source", {})
                else:
                    source = getattr(ex, "source", None)
                    source = (
                        source.__dict__
                        if source and hasattr(source, "__dict__")
                        else (source or {})
                    )

                year = source.get("year", 0)
                if year <= 0:
                    continue

                # Build flat context for feature extraction
                flat_ctx = {
                    "year": year,
                    "role": source.get("role"),
                    "section": source.get("section_type"),
                    "exam_type": source.get("exam_type"),
                    "sentence_role": source.get("sentence_role"),
                    "text": ex.get("text", "") if isinstance(ex, dict) else getattr(ex, "text", ""),
                }
                wf.contexts_raw.append(flat_ctx)

                # WSD tracking: which sense was used in which year
                wf.wsd_year_sense_map[year][s_idx] += 1
                role = source.get("role") or "none"
                wf.wsd_sense_role_map[s_idx][role] += 1

        # 3. Relations
        if isinstance(entry, dict):
            wf.synonym_count = len(entry.get("synonyms") or [])
            wf.antonym_count = len(entry.get("antonyms") or [])
        else:
            wf.synonym_count = len(getattr(entry, "synonyms", []) or [])
            wf.antonym_count = len(getattr(entry, "antonyms", []) or [])

        # 4. Essay contexts
        wf.essay_years = [
            occ["year"] for occ in wf.contexts_raw if occ.get("section") == SectionType.ESSAY
        ]

        # 5. Post-process derived fields
        # CRITICAL: Only count OFFICIAL exams as "tested", NOT REF/TRIAL
        wf.years_appeared = sorted(
            list(
                {
                    occ["year"]
                    for occ in wf.contexts_raw
                    if occ.get("exam_type") in OFFICIAL_EXAM_TYPES and occ.get("year")
                }
            )
        )
        wf.years_tested = sorted(
            list(
                {
                    occ["year"]
                    for occ in wf.contexts_raw
                    if occ.get("role") in TESTED_ROLES
                    and occ.get("exam_type") in OFFICIAL_EXAM_TYPES
                }
            )
        )

        return wf

    def extract_feature_vector(
        self,
        word_data: WordFeatureData,
        target_year: int,
        external_features: dict[str, float] | None = None,
    ) -> list[float] | None:
        """Extract a fixed-length feature vector filtered by target_year."""

        def is_historically_available(occ):
            src = occ.get("source", {})
            y = occ.get("year") or src.get("year", 0)
            if y < target_year:
                return True
            if y == target_year:
                et = occ.get("exam_type") or src.get("exam_type")
                if et in [ExamType.GSAT_REF, ExamType.GSAT_TRIAL]:
                    return True
            return False

        history = [occ for occ in word_data.contexts_raw if is_historically_available(occ)]
        processed_history = []
        for occ in history:
            src = occ.get("source", {})
            processed_history.append(
                {
                    "year": occ.get("year") or src.get("year", 0),
                    "role": occ.get("role") or src.get("role"),
                    "section": occ.get("section") or src.get("section") or src.get("section_type"),
                    "exam_type": occ.get("exam_type") or src.get("exam_type"),
                    "sentence_role": occ.get("sentence_role") or src.get("sentence_role"),
                }
            )

        official_history = [occ for occ in processed_history if occ.get("exam_type") in OFFICIAL_EXAM_TYPES]
        ref_history = [occ for occ in processed_history if occ.get("exam_type") == ExamType.GSAT_REF]
        trial_history = [occ for occ in processed_history if occ.get("exam_type") == ExamType.GSAT_TRIAL]

        total_occ = len(official_history)

        years_appeared = sorted(list({occ["year"] for occ in official_history if occ["year"] > 0}))
        years_tested = sorted(
            list(
                {
                    occ["year"]
                    for occ in official_history
                    if occ.get("role") in TESTED_ROLES
                }
            )
        )
        years_active = sorted(
            list(
                {
                    occ["year"]
                    for occ in official_history
                    if occ.get("role") in ACTIVE_TESTED_ROLES
                }
            )
        )

        role_counts = defaultdict(int)
        section_counts = defaultdict(int)
        exam_counts = defaultdict(int)
        sentence_role_counts = defaultdict(int)
        cloze_as_answer_count = 0

        for occ in official_history:
            role_counts[occ.get("role")] += 1
            section_counts[occ.get("section")] += 1
            exam_counts[occ.get("exam_type")] += 1
            sentence_role_counts[occ.get("sentence_role")] += 1
            if (
                occ.get("role") == AnnotationRole.CORRECT_ANSWER
                and occ.get("section") == SectionType.CLOZE
            ):
                cloze_as_answer_count += 1

        year_spread = years_appeared[-1] - years_appeared[0] + 1 if years_appeared else 0
        tested_year_spread = years_tested[-1] - years_tested[0] + 1 if years_tested else 0

        last_tested = years_tested[-1] if years_tested else 0
        gap = target_year - last_tested if last_tested > 0 else 20
        ans_count = role_counts.get(AnnotationRole.CORRECT_ANSWER, 0) + role_counts.get(
            AnnotationRole.TESTED_KEYWORD, 0
        )
        dist_count = role_counts.get(AnnotationRole.DISTRACTOR, 0)

        f = []

        # 1. Basic (7)
        f.append(float(total_occ))
        f.append(math.log1p(total_occ))
        f.append(float(len(years_tested)))
        f.append(float(len(years_active)))
        f.append(float(year_spread))
        f.append(float(tested_year_spread))
        f.append(
            year_spread / (target_year - (years_appeared[0] if years_appeared else target_year) + 1)
            if years_appeared
            else 0.0
        )

        # 2. Official (2)
        f.append(1.0 if word_data.in_official else 0.0)
        f.append(float(word_data.level or 0))

        # 3. Linguistic (5)
        f.append(float(word_data.length))
        f.append(float(word_data.syllables))
        f.append(1.0 if word_data.has_common_prefix else 0.0)
        f.append(1.0 if word_data.has_common_suffix else 0.0)
        f.append(float(word_data.wn_synset_count))
        f.append(word_data.wn_avg_hypernyms)
        f.append(word_data.wn_avg_hyponyms)
        f.append(word_data.wn_avg_depth)
        f.append(float(word_data.wn_domain_diversity))
        f.append(float(word_data.synonym_count))
        f.append(float(word_data.antonym_count))

        # 4. Distractor Analysis (3)
        f.append(float(dist_count))
        f.append(float(ans_count))
        f.append(ans_count / max(1, dist_count + ans_count))

        # 5. Temporal (4)
        f.append(10.0 / (gap + 1.0))  # recency_score
        f.append(float(gap))  # years_since
        f.append(float(year_spread))  # raw_appearance_spread
        f.append(year_spread / 20.0)  # normalized_appearance_spread

        # 6. Curriculum (2)
        recent_5y = [y for y in years_appeared if y >= target_year - 5]
        f.append(float(len(recent_5y)))
        f.append(1.0 if recent_5y else 0.0)

        # 7. Roles (8)
        f.append(float(ans_count))  # role_correct_answer
        f.append(float(dist_count))  # role_distractor
        f.append(
            float(sentence_role_counts.get(SentenceRole.QUESTION_PROMPT, 0))
        )  # role_question_prompt
        f.append(float(sentence_role_counts.get(SentenceRole.PASSAGE, 0)))  # role_passage_word
        f.append(float(sentence_role_counts.get(SentenceRole.OPTION, 0)))  # role_option
        f.append(float(role_counts.get("none", 0)))  # role_none
        f.append(ans_count / max(1, total_occ))  # role_correct_ratio
        f.append(dist_count / max(1, total_occ))  # role_distractor_ratio

        # 8. Sections (5)
        f.append(float(section_counts.get(SectionType.VOCABULARY, 0)))
        f.append(float(section_counts.get(SectionType.CLOZE, 0)))
        f.append(float(section_counts.get(SectionType.READING, 0)))
        f.append(float(section_counts.get(SectionType.TRANSLATION, 0)))
        f.append(float(section_counts.get(SectionType.ESSAY, 0)))

        # 9. Exams (5)
        gsat_count = exam_counts.get(ExamType.GSAT, 0) + exam_counts.get(ExamType.GSAT_MAKEUP, 0)
        ast_count = exam_counts.get(ExamType.AST, 0) + exam_counts.get(ExamType.AST_MAKEUP, 0)
        trial_count = len(trial_history)
        f.append(float(gsat_count))
        f.append(float(ast_count))
        f.append(float(trial_count))
        f.append(gsat_count / max(1, total_occ))
        f.append(ast_count / max(1, total_occ))

        # 10. Advanced Temporal (4)
        recent_3 = len([y for y in years_appeared if y >= target_year - 3])
        prev_7 = len([y for y in years_appeared if target_year - 10 <= y < target_year - 3])
        f.append(float(recent_3 - (prev_7 / 7.0 * 3.0)))  # frequency_trend

        gaps = [years_tested[i] - years_tested[i - 1] for i in range(1, len(years_tested))]
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        f.append(float(avg_gap))
        f.append(
            float((target_year - last_tested) - avg_gap) if last_tested > 0 and avg_gap > 0 else 0
        )
        f.append(float(np.var(gaps)) if len(gaps) > 1 else 0)  # consistency_variance

        # 11. Essay (2)
        f.append(1.0 if target_year in word_data.essay_years else 0.0)
        f.append(1.0 if any(y < target_year for y in word_data.essay_years) else 0.0)

        # 12. High Weight (1)
        total_structural = float(
            section_counts.get(SectionType.READING, 0)
            + section_counts.get(SectionType.VOCABULARY, 0)
        )
        f.append(total_structural / max(1, total_occ))

        # 13. Tested Only (3)
        f.append(float(len(years_tested)))  # tested_years_count
        t_recent_3 = len([y for y in years_tested if y >= target_year - 3])
        t_prev_7 = len([y for y in years_tested if target_year - 10 <= y < target_year - 3])
        f.append(float(t_recent_3 - (t_prev_7 / 7.0 * 3.0)))  # tested_trend
        f.append(float(tested_year_spread))  # tested_year_spread_val

        # 14. Age (1)
        first = years_appeared[0] if years_appeared else target_year
        f.append(float(target_year - first))

        # 15. Regularity (1)
        f.append(1.0 / (1.0 + np.var(gaps)) if len(gaps) > 1 else 0.5)

        # 16. Phase 3 (12)
        valid_wsd_map = defaultdict(int)
        total_wsd = 0
        for y, s_map in word_data.wsd_year_sense_map.items():
            if y < target_year:
                for s_idx, cnt in s_map.items():
                    valid_wsd_map[s_idx] += cnt
                    total_wsd += cnt

        f.append(float(len(valid_wsd_map)) if valid_wsd_map else 1.0)  # sense_count_proxy
        wsd_entropy_val = 0.0
        if total_wsd > 0:
            probs = [c / total_wsd for c in valid_wsd_map.values()]
            wsd_entropy_val = -sum(p * math.log(p) for p in probs if p > 0)
        f.append(wsd_entropy_val)  # tested_sense_diversity

        f.append(float(len(years_tested)) / max(1, total_occ))  # tested_sense_ratio
        f.append(
            max(valid_wsd_map.values()) / max(1, total_wsd) if valid_wsd_map else 1.0
        )  # primary_sense_dominance_proxy

        f.append(section_counts.get(SectionType.CLOZE, 0) / max(1, total_occ))  # role_cloze_ratio
        f.append(
            sentence_role_counts.get(SentenceRole.PASSAGE, 0) / max(1, total_occ)
        )  # role_passage_ratio
        f.append(
            sentence_role_counts.get(SentenceRole.OPTION, 0) / max(1, total_occ)
        )  # role_option_ratio
        f.append(
            cloze_as_answer_count / max(1, section_counts.get(SectionType.CLOZE, 0))
        )  # cloze_as_answer_ratio

        ref_count = len(ref_history)
        trial_count = len(trial_history)
        f.append(float(ref_count))  # ref_exam_count

        last_ref_year = max([occ["year"] for occ in ref_history], default=0)
        f.append(float(target_year - last_ref_year) if last_ref_year > 0 else 20.0)  # ref_recency
        f.append(float(trial_count))  # trial_exam_count

        last_signal_year = max([occ["year"] for occ in ref_history + trial_history], default=0)
        last_official_test = years_tested[-1] if years_tested else 0
        if last_signal_year and last_official_test:
            f.append(float(last_official_test - last_signal_year))
        elif last_signal_year:
            f.append(float(target_year - last_signal_year))
        else:
            f.append(0.0)

        # 18. Phase 9 / WSD Advanced (6)
        f.append(wsd_entropy_val)  # wsd_entropy
        f.append(
            max(valid_wsd_map.values()) / max(1, total_wsd) if valid_wsd_map else 1.0
        )  # wsd_max_ratio
        f.append(float(len(valid_wsd_map)))  # wsd_sense_count

        active_sense_count = 0
        question_prompt_matches = 0
        sense_last_years = {}
        for s_idx in valid_wsd_map:
            r_map = word_data.wsd_sense_role_map.get(s_idx, {})
            if (
                r_map.get(AnnotationRole.CORRECT_ANSWER, 0)
                + r_map.get(AnnotationRole.TESTED_KEYWORD, 0)
                > 0
            ):
                active_sense_count += 1
            question_prompt_matches += r_map.get(SentenceRole.QUESTION_PROMPT, 0)
            last_y = max(
                [
                    y
                    for y, s_m in word_data.wsd_year_sense_map.items()
                    if s_idx in s_m and y < target_year
                ],
                default=0,
            )
            if last_y > 0:
                sense_last_years[s_idx] = last_y

        f.append(float(active_sense_count))  # wsd_active_sense_count
        f.append(
            question_prompt_matches / max(1, total_wsd) if total_wsd > 0 else 0.0
        )  # wsd_question_prompt_ratio

        wsd_recency_spread = 0.0
        if len(sense_last_years) > 1:
            wsd_recency_spread = float(np.var(list(sense_last_years.values())))
        f.append(wsd_recency_spread)  # wsd_recency_spread

        # 19. External & Difficulty (3)
        if external_features:
            f.append(external_features.get("survival_hazard", 0.5))
            f.append(external_features.get("synonym_tested_freq", 0.0))
        else:
            f.append(0.5)
            f.append(0.0)

        f.append(1.0 if 3 <= (word_data.level or 0) <= 5 else 0.0)  # level_difficulty_match

        # FINAL CHECK: Ensure correct feature count
        # Basic(7), Official(2), Linguistic(11), Distractor(3), Temporal(4), Curriculum(2), Roles(8), Sections(5), Exams(5), AdvTemp(4), Essay(2), HighWeight(1), TestedOnly(3), Age(1), Regularity(1), Phase3(12), Phrase(3), Phase9(6), Ext(3)
        # 7+2+11+3+4+2+8+5+5+4+2+1+3+1+1+12+3+6+3 = 83
        if len(f) != len(FEATURE_NAMES):
            raise ValueError(
                f"Feature vector length mismatch: Expected {len(FEATURE_NAMES)} (83), got {len(f)}"
            )

        return f


def get_feature_names() -> list[str]:
    return FEATURE_NAMES.copy()


def extract_features_for_word(
    entry: dict[str, Any],
    distractor_groups: list[dict],
    essay_topics: list[dict] | None = None,
    current_year: int = 114,
) -> list[float] | None:
    """Wrapper for backward compatibility and ad-hoc extraction."""
    extractor = FeatureExtractor(current_year=current_year)
    # Distractor/Essay indexing logic can be added here if needed,
    # but the new architecture pre-calculates many roles.
    word_data = extractor.extract_word_data(entry)
    return extractor.extract_feature_vector(word_data, target_year=current_year)

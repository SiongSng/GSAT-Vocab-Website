"""
Constants and weight configurations for GSAT vocabulary importance prediction.

108 課綱 Timeline:
- Year 108 (2019): Students enter high school under new curriculum
- Year 110 (2021): Trial exam (試辦考試)
- Year 111 (2022): First official GSAT under new curriculum + reference papers (參考試卷)

So the actual exam impact starts from year 111, with 110/111 as transition period.
"""

CURRICULUM_CUTOFF_YEAR = 111

TRIAL_YEARS = {110, 111}

ROLE_WEIGHTS = {
    "correct_answer": 1.0,
    "distractor": 0.4,
    "tested_keyword": 1.2,
    "notable_pattern": 0.7,
    "notable_phrase": 0.5,
}

SECTION_WEIGHTS = {
    "reading": 1.8,
    "structure": 1.2,
    "vocabulary": 1.0,
    "discourse": 0.9,
    "mixed": 1.0,
    "cloze": 0.5,
    "translation": 0.5,
}

EXAM_WEIGHTS = {
    "gsat": 1.2,
    "gsat_ref": 1.1,
    "gsat_makeup": 1.0,
    "gsat_trial": 1.0,
    "ast": 0.6,
    "ast_makeup": 0.5,
}

OFFICIAL_BONUS_COEFFICIENT = 0.54
YEAR_SPREAD_COEFFICIENT = 0.05
RECENCY_COEFFICIENT = 0.04
DISTRACTOR_PARTNER_COEFFICIENT = 0.02

PRE_CURRICULUM_MULTIPLIER = 1.12
POST_CURRICULUM_MULTIPLIER = 0.90

TRIAL_PERIOD_MULTIPLIER = 1.05

MAX_YEAR_SPREAD_CAP = 10
MAX_DISTRACTOR_PARTNER_CAP = 10
RECENCY_WINDOW_YEARS = 3

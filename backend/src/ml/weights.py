"""
Constants and weight configurations for GSAT vocabulary importance prediction.

108 課綱 Timeline:
- Year 108 (2019): Students enter high school under new curriculum
- Year 110 (2021): Trial exam (試辦考試)
- Year 111 (2022): First official GSAT under new curriculum + reference papers (參考試卷)

So the actual exam impact starts from year 111, with 110/111 as transition period.

Exam Temporal Order (within the same year Y):
- gsat_ref_Y: Released BEFORE the official GSAT → can be used to predict Y
- gsat_Y: The official exam → ground truth for Y
- gsat_makeup_Y: Released AFTER official GSAT → can only predict Y+1

Note: AST (指考) is now treated equally because post-AST-abolition,
GSAT difficulty is trending towards AST level.
"""

CURRICULUM_CUTOFF_YEAR = 111

TRIAL_YEARS = {110, 111}

# Temporal order within the same year (lower = earlier in time)
EXAM_TEMPORAL_ORDER = {
    "gsat_ref": 0,      # Before official exam
    "gsat_trial": 0,    # Before official exam
    "gsat": 1,          # Official exam
    "ast": 1,           # Official exam (same temporal slot)
    "gsat_makeup": 2,   # After official exam
    "ast_makeup": 2,    # After official exam
}

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
    "gsat_ref": 1.3,      # Higher weight: direction indicator
    "gsat_makeup": 1.0,
    "gsat_trial": 1.2,    # Higher weight: direction indicator
    "ast": 1.0,           # Changed from 0.6 to 1.0 (equal weight)
    "ast_makeup": 0.8,    # Slightly lower but not heavily discounted
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

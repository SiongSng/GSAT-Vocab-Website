"""Validation utilities to ensure PLAN.md compliance before output."""

import logging
from dataclasses import dataclass

from ..models import VocabEntry

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    lemma: str
    issue_type: str
    message: str


def validate_entry(entry: VocabEntry) -> list[ValidationIssue]:
    """Validate a single VocabEntry against PLAN.md requirements."""
    issues = []

    # 1. senses.length >= 1
    if not entry.senses:
        issues.append(
            ValidationIssue(
                lemma=entry.lemma,
                issue_type="no_senses",
                message="Entry has no senses (PLAN requires at least 1)",
            )
        )
        return issues  # Can't check sense-level issues without senses

    lemma_key = entry.lemma.lower().replace(" ", "_")

    for sense in entry.senses:
        # sense_id should be stable and start with lemma_key_
        if not sense.sense_id or not sense.sense_id.lower().startswith(f"{lemma_key}_"):
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="invalid_sense_id",
                    message=f"Sense id {sense.sense_id} should start with {lemma_key}_",
                )
            )
        # 2. zh_def and en_def must be non-empty
        if not sense.zh_def or not sense.zh_def.strip():
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_zh_def",
                    message=f"Sense {sense.sense_id} has empty zh_def",
                )
            )

        if not sense.en_def or not sense.en_def.strip():
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_en_def",
                    message=f"Sense {sense.sense_id} has empty en_def",
                )
            )

        # 3. Each sense needs generated_example
        if not sense.generated_example:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_generated_example",
                    message=f"Sense {sense.sense_id} has no generated example",
                )
            )

        # 4. tested_in_exam=true must have at least one real example with source
        if sense.tested_in_exam and not sense.examples:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="tested_no_real_example",
                    message=f"Sense {sense.sense_id} has tested_in_exam=true but no real examples",
                )
            )

        # 4b. All real examples must have valid source info
        for ex in sense.examples:
            if not ex.source or not ex.source.year:
                issues.append(
                    ValidationIssue(
                        lemma=entry.lemma,
                        issue_type="example_missing_source",
                        message=f"Sense {sense.sense_id} has example without valid source",
                    )
                )

    # 5. pos field should include all sense POS types (normalize to uppercase abbr)
    def _normalize_pos(pos: str) -> str:
        p = pos.strip().upper()
        mapping = {
            "NOUN": "NOUN",
            "VERB": "VERB",
            "ADJECTIVE": "ADJ",
            "ADJ": "ADJ",
            "ADVERB": "ADV",
            "ADV": "ADV",
        }
        return mapping.get(p, p)

    if entry.type == "word" and entry.pos:
        sense_pos_types = {_normalize_pos(s.pos) for s in entry.senses}
        entry_pos_set = {p.upper() for p in entry.pos}
        missing_pos = sense_pos_types - entry_pos_set - {"PHRASE"}
        if missing_pos:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="pos_mismatch",
                    message=f"Entry pos {entry.pos} missing sense POS types: {missing_pos}",
                )
            )

    # 6. tier-specific checks
    tier_val = entry.tier.value if hasattr(entry.tier, "value") else entry.tier
    # tested: if has distractors (confusion_notes expected), ensure not empty
    if (
        tier_val == "tested"
        and entry.confusion_notes is not None
        and any(
            not cn.memory_tip.strip() or not cn.distinction.strip() for cn in entry.confusion_notes
        )
    ):
        issues.append(
            ValidationIssue(
                lemma=entry.lemma,
                issue_type="invalid_confusion_note",
                message="confusion_notes must have distinction and memory_tip",
            )
        )
    # root_info: only for level>=2 and tiers tested/translation; forbid for level 1
    if entry.level == 1:
        if entry.root_info is not None:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="root_for_level1",
                    message="Level 1 should not have root_info",
                )
            )
    else:
        if (
            entry.level is not None
            and entry.level >= 2
            and tier_val in ("tested", "translation")
            and entry.root_info is None
        ):
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_root_info",
                    message="root_info required for tested/translation level>=2",
                )
            )
        if entry.root_info and not entry.root_info.memory_strategy:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_memory_strategy",
                    message="root_info exists but memory_strategy is empty",
                )
            )

    return issues


def validate_all_entries(
    entries: list[VocabEntry],
) -> tuple[list[VocabEntry], list[ValidationIssue]]:
    """Validate all entries and return (valid_entries, all_issues).

    Returns entries that pass critical validation (have at least 1 sense with definitions).
    """
    all_issues = []
    valid_entries = []

    for entry in entries:
        issues = validate_entry(entry)
        all_issues.extend(issues)

        # Critical issues that would make entry unusable
        critical_types = {"no_senses"}
        has_critical = any(i.issue_type in critical_types for i in issues)

        if not has_critical:
            valid_entries.append(entry)
        else:
            logger.warning(f"Excluding {entry.lemma} due to critical issues")

    # Log summary
    if all_issues:
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1
        logger.warning(f"Validation found {len(all_issues)} issues: {issue_counts}")
    else:
        logger.info("All entries passed validation")

    return valid_entries, all_issues

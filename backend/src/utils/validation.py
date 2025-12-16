import logging
from dataclasses import dataclass

from ..models import PatternEntry, VocabEntry, WordEntry

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    lemma: str
    issue_type: str
    message: str


def validate_entry(entry: VocabEntry) -> list[ValidationIssue]:
    issues = []

    if isinstance(entry, PatternEntry):
        if not entry.subtypes:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="no_subtypes",
                    message="Pattern entry has no subtypes",
                )
            )
            return issues

        if not entry.teaching_explanation or not entry.teaching_explanation.strip():
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_teaching_explanation",
                    message="Pattern entry has empty teaching_explanation",
                )
            )

        for subtype in entry.subtypes:
            if not subtype.generated_example:
                issues.append(
                    ValidationIssue(
                        lemma=entry.lemma,
                        issue_type="missing_generated_example",
                        message=f"Subtype {subtype.subtype} has no generated example",
                    )
                )

        return issues

    if not entry.senses:
        issues.append(
            ValidationIssue(
                lemma=entry.lemma,
                issue_type="no_senses",
                message="Entry has no senses (requires at least 1)",
            )
        )
        return issues

    lemma_key = entry.lemma.lower().replace(" ", "_")

    for sense in entry.senses:
        if not sense.sense_id or not sense.sense_id.lower().startswith(f"{lemma_key}_"):
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="invalid_sense_id",
                    message=f"Sense id {sense.sense_id} should start with {lemma_key}_",
                )
            )

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

        if not sense.generated_example:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="missing_generated_example",
                    message=f"Sense {sense.sense_id} has no generated example",
                )
            )

        for ex in sense.examples:
            if not ex.source or not ex.source.year:
                issues.append(
                    ValidationIssue(
                        lemma=entry.lemma,
                        issue_type="example_missing_source",
                        message=f"Sense {sense.sense_id} has example without valid source",
                    )
                )

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

    if isinstance(entry, WordEntry) and entry.pos:
        sense_pos_types = {_normalize_pos(s.pos) for s in entry.senses if s.pos}
        entry_pos_set = {p.upper() for p in entry.pos}
        missing_pos = sense_pos_types - entry_pos_set - {"PHRASE", "OTHER"}
        if missing_pos:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="pos_mismatch",
                    message=f"Entry pos {entry.pos} missing sense POS types: {missing_pos}",
                )
            )

    if isinstance(entry, WordEntry):
        if entry.confusion_notes:
            for cn in entry.confusion_notes:
                if not cn.memory_tip.strip() or not cn.distinction.strip():
                    issues.append(
                        ValidationIssue(
                            lemma=entry.lemma,
                            issue_type="invalid_confusion_note",
                            message="confusion_notes must have distinction and memory_tip",
                        )
                    )

        if entry.level == 1 and entry.root_info is not None:
            issues.append(
                ValidationIssue(
                    lemma=entry.lemma,
                    issue_type="root_for_level1",
                    message="Level 1 should not have root_info",
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
    all_issues = []
    valid_entries = []

    for entry in entries:
        issues = validate_entry(entry)
        all_issues.extend(issues)

        critical_types = {"no_senses", "no_subtypes"}
        has_critical = any(i.issue_type in critical_types for i in issues)

        if not has_critical:
            valid_entries.append(entry)
        else:
            logger.warning(f"Excluding {entry.lemma} due to critical issues")

    if all_issues:
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1
        logger.warning(f"Validation found {len(all_issues)} issues: {issue_counts}")
    else:
        logger.info("All entries passed validation")

    return valid_entries, all_issues

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ..models import DistractorGroup, VocabDatabase, VocabEntry, VocabMetadata
from ..utils.validation import ValidationIssue, validate_all_entries

logger = logging.getLogger(__name__)


def build_database(
    entries: list[VocabEntry],
    distractor_groups: list[DistractorGroup],
    min_year: int,
    max_year: int,
) -> VocabDatabase:
    # Validate entries before building database
    valid_entries, issues = validate_all_entries(entries)

    if issues:
        logger.warning(f"Validation found {len(issues)} issues in {len(entries)} entries")
        for issue in issues[:10]:
            logger.warning(f"  {issue.lemma}: {issue.message}")
        if len(issues) > 10:
            logger.warning(f"  ... and {len(issues) - 10} more issues")

    count_by_type = {"word": 0, "phrase": 0, "pattern": 0}
    count_by_tier = {"tested": 0, "translation": 0, "phrase": 0, "basic": 0}
    for entry in valid_entries:
        if entry.type in count_by_type:
            count_by_type[entry.type] += 1
        if entry.tier.value in count_by_tier:
            count_by_tier[entry.tier.value] += 1

    metadata = VocabMetadata(
        exam_year_range={"min": min_year, "max": max_year},
        total_entries=len(valid_entries),
        count_by_type=count_by_type,
        count_by_tier=count_by_tier,
    )

    return VocabDatabase(
        version="2.0.0",
        generated_at=datetime.now(UTC).isoformat(),
        metadata=metadata,
        entries=valid_entries,
        distractor_groups=distractor_groups,
    )


def write_output(
    database: VocabDatabase,
    output_path: Path,
    errors_path: Path | None = None,
) -> tuple[int, list[ValidationIssue]]:
    # Re-validate to collect all issues for error report
    _, all_issues = validate_all_entries(database.entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    def exclude_empty_arrays(obj):
        if isinstance(obj, dict):
            return {
                k: exclude_empty_arrays(v)
                for k, v in obj.items()
                if not (isinstance(v, list) and len(v) == 0)
            }
        elif isinstance(obj, list):
            return [exclude_empty_arrays(item) for item in obj]
        return obj

    data = exclude_empty_arrays(database.model_dump(exclude_none=True))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if errors_path and all_issues:
        error_data = [
            {
                "lemma": issue.lemma,
                "type": issue.issue_type,
                "message": issue.message,
            }
            for issue in all_issues
        ]
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)

    return len(database.entries), all_issues

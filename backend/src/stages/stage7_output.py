import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from ..models import (
    PatternEntry,
    PhraseEntry,
    VocabDatabase,
    VocabEntry,
    VocabMetadata,
    WordEntry,
)

logger = logging.getLogger(__name__)


def build_database(
    entries: list[VocabEntry],
    min_year: int,
    max_year: int,
) -> VocabDatabase:
    words: list[WordEntry] = []
    phrases: list[PhraseEntry] = []
    patterns: list[PatternEntry] = []

    for entry in entries:
        if isinstance(entry, WordEntry):
            words.append(entry)
        elif isinstance(entry, PhraseEntry):
            phrases.append(entry)
        elif isinstance(entry, PatternEntry):
            patterns.append(entry)

    count_by_type = {
        "word": len(words),
        "phrase": len(phrases),
        "pattern": len(patterns),
    }

    metadata = VocabMetadata(
        exam_year_range={"min": min_year, "max": max_year},
        total_entries=len(entries),
        count_by_type=count_by_type,
    )

    return VocabDatabase(
        version="3.0.0",
        generated_at=datetime.now(UTC).isoformat(),
        metadata=metadata,
        words=words,
        phrases=phrases,
        patterns=patterns,
    )


def write_output(
    database: VocabDatabase,
    output_path: Path,
) -> None:
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

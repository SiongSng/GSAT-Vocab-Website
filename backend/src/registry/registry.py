import hashlib
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Literal, NamedTuple

from .models import RegistrySense

SenseSource = Literal["dictionaryapi", "llm_generated", "manual", "wordnet"]
WSDSource = Literal["graded_wsd", "llm"]

WSD_MODEL_VERSION = "graded-wsd-1.0"
WSD_LLM_VERSION = "llm-v1"


class WSDCacheEntry(NamedTuple):
    sense_idx: int | None
    source: WSDSource
    model_version: str

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_PATH = (
    Path(__file__).parent.parent.parent / "data" / "registry" / "sense_registry.db"
)


def _pos_to_abbrev(pos: str | None) -> str:
    if pos is None:
        return "phr"
    mapping = {
        "NOUN": "n",
        "VERB": "v",
        "ADJ": "adj",
        "ADV": "adv",
        "PRON": "pron",
        "DET": "det",
        "CONJ": "conj",
        "PREP": "prep",
        "AUX": "aux",
    }
    return mapping.get(pos.upper(), "x")


def _normalize_lemma(lemma: str) -> str:
    return lemma.strip().lower().replace(" ", "_")


def _row_to_sense(row: sqlite3.Row) -> RegistrySense:
    return RegistrySense(
        sense_id=row["sense_id"],
        lemma=row["lemma"],
        pos=row["pos"],
        source=row["source"],
        definition=row["definition"],
    )


class Registry:
    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_REGISTRY_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # WAL mode: much faster writes, allows concurrent reads during writes
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS senses (
                    sense_id TEXT PRIMARY KEY,
                    lemma TEXT NOT NULL,
                    pos TEXT,
                    source TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    sense_order INTEGER,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                """
            )
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_senses_lemma ON senses(lemma);")
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_senses_lemma_source ON senses(lemma, source);"
            )
            self._migrate_add_sense_order()
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sense_generation_cache (
                    lemma TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (lemma, cache_key)
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_generation_cache_lemma ON sense_generation_cache(lemma);"
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS wsd_cache (
                    cache_key TEXT PRIMARY KEY,
                    sense_idx INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                """
            )
            self.conn.commit()

    def _migrate_add_sense_order(self) -> None:
        cursor = self.conn.execute("PRAGMA table_info(senses)")
        columns = {row[1] for row in cursor.fetchall()}
        if "sense_order" not in columns:
            self.conn.execute("ALTER TABLE senses ADD COLUMN sense_order INTEGER")
            logger.info("Migrated senses table: added sense_order column")

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def _get_existing_sense(
        self, lemma: str, pos: str | None, source: str, definition: str
    ) -> RegistrySense | None:
        query = """
            SELECT * FROM senses
            WHERE lemma = ? AND COALESCE(pos, '') = COALESCE(?, '')
              AND source = ? AND definition = ?
        """
        with self._lock:
            row = self.conn.execute(query, (lemma, pos, source, definition)).fetchone()
        if row:
            return _row_to_sense(row)
        return None

    def _get_next_reg_index(self, lemma: str, pos_abbrev: str) -> int:
        query = """
            SELECT sense_id FROM senses
            WHERE lemma = ? AND sense_id LIKE ?
        """
        pattern = f"{_normalize_lemma(lemma)}.{pos_abbrev}.reg%"
        with self._lock:
            rows = self.conn.execute(query, (lemma, pattern)).fetchall()
        max_idx = 0
        for row in rows:
            sid: str = row["sense_id"]
            try:
                suffix = sid.split(".reg")[-1]
                max_idx = max(max_idx, int(suffix))
            except ValueError:
                continue
        return max_idx + 1

    def _generate_sense_id(self, lemma: str, pos: str | None, source: str, definition: str) -> str:
        lemma_key = _normalize_lemma(lemma)
        pos_abbrev = _pos_to_abbrev(pos)
        if source == "dictionaryapi":
            digest = hashlib.sha1(definition.strip().lower().encode("utf-8")).hexdigest()[:8]
            return f"{lemma_key}.{pos_abbrev}.dict{digest}"
        if source == "wordnet":
            digest = hashlib.sha1(definition.strip().lower().encode("utf-8")).hexdigest()[:6]
            return f"{lemma_key}.{pos_abbrev}.wn{digest}"
        reg_index = self._get_next_reg_index(lemma, pos_abbrev)
        return f"{lemma_key}.{pos_abbrev}.reg{reg_index}"

    def get_senses_for_lemma(self, lemma: str) -> list[RegistrySense]:
        with self._lock:
            rows = self.conn.execute(
                """SELECT * FROM senses WHERE lemma = ?
                   ORDER BY sense_order ASC NULLS LAST, created_at ASC""",
                (lemma,),
            ).fetchall()
        return [_row_to_sense(r) for r in rows]

    def get_sense(self, sense_id: str) -> RegistrySense | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM senses WHERE sense_id = ?", (sense_id,)
            ).fetchone()
        if row:
            return _row_to_sense(row)
        return None

    async def add_sense(
        self,
        lemma: str,
        pos: str | None,
        definition: str,
        source: SenseSource = "llm_generated",
        sense_id: str | None = None,
        sense_order: int | None = None,
    ) -> str:
        lemma = lemma.strip()
        definition = definition.strip()
        existing = self._get_existing_sense(lemma, pos, source, definition)
        if existing:
            if sense_order is not None:
                with self._lock:
                    self.conn.execute(
                        "UPDATE senses SET sense_order = ? WHERE sense_id = ?",
                        (sense_order, existing.sense_id),
                    )
                    self.conn.commit()
            return existing.sense_id

        if sense_id is None:
            sense_id = self._generate_sense_id(lemma, pos, source, definition)

        payload = RegistrySense(
            sense_id=sense_id,
            lemma=lemma,
            pos=pos,
            source=source,
            definition=definition,
        )

        with self._lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO senses (
                    sense_id, lemma, pos, source, definition, sense_order
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.sense_id,
                    payload.lemma,
                    payload.pos,
                    payload.source,
                    payload.definition,
                    sense_order,
                ),
            )
            self.conn.commit()

        logger.info(f"Added new sense: {sense_id} (source={source}, order={sense_order})")
        return sense_id

    def get_generation_cache(self, lemma: str, cache_key: str) -> str | None:
        query = """
            SELECT payload FROM sense_generation_cache
            WHERE lemma = ? AND cache_key = ?
        """
        with self._lock:
            row = self.conn.execute(query, (_normalize_lemma(lemma), cache_key)).fetchone()
        if row:
            return row["payload"]
        return None

    def upsert_generation_cache(self, lemma: str, cache_key: str, payload: str) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO sense_generation_cache (lemma, cache_key, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(lemma, cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = datetime('now');
                """,
                (_normalize_lemma(lemma), cache_key, payload),
            )
            self.conn.commit()

    def save(self) -> None:
        with self._lock:
            self.conn.commit()

    def get_wsd_cache_batch(self, cache_keys: list[str]) -> dict[str, WSDCacheEntry]:
        """Get multiple WSD cache entries.

        Returns: {cache_key: WSDCacheEntry} for found entries.
        """
        if not cache_keys:
            return {}
        placeholders = ",".join("?" * len(cache_keys))
        with self._lock:
            rows = self.conn.execute(
                f"SELECT cache_key, sense_idx, source, model_version FROM wsd_cache "
                f"WHERE cache_key IN ({placeholders})",
                cache_keys,
            ).fetchall()
        result: dict[str, WSDCacheEntry] = {}
        for row in rows:
            idx = row["sense_idx"]
            result[row["cache_key"]] = WSDCacheEntry(
                sense_idx=None if idx == -1 else idx,
                source=row["source"],
                model_version=row["model_version"],
            )
        return result

    def set_wsd_cache_batch(
        self,
        entries: dict[str, tuple[int | None, WSDSource, str]],
    ) -> None:
        """Batch insert WSD cache entries.

        Args:
            entries: {cache_key: (sense_idx, source, model_version)}
        """
        if not entries:
            return
        data = [
            (key, -1 if sense_idx is None else sense_idx, source, version)
            for key, (sense_idx, source, version) in entries.items()
        ]
        with self._lock:
            self.conn.executemany(
                """
                INSERT INTO wsd_cache (cache_key, sense_idx, source, model_version)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    sense_idx = excluded.sense_idx,
                    source = excluded.source,
                    model_version = excluded.model_version,
                    created_at = datetime('now');
                """,
                data,
            )
            self.conn.commit()

    def __len__(self) -> int:
        with self._lock:
            row = self.conn.execute("SELECT COUNT(*) as cnt FROM senses").fetchone()
        return int(row["cnt"]) if row else 0

    def __contains__(self, sense_id: str) -> bool:
        return self.get_sense(sense_id) is not None

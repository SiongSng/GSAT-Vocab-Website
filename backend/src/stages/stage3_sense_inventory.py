import asyncio
import contextlib
import logging
import random
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from ..llm import get_llm_client
from ..llm.client import LLMClient, ModelTier
from ..llm.prompts_stage3 import (
    STAGE3_DICT_FILTER_BATCH_PROMPT,
    STAGE3_DICT_FILTER_SYSTEM,
    STAGE3_LLMS_DEFINE_PHRASE_PROMPT,
    STAGE3_LLMS_DEFINE_PROMPT,
    STAGE3_LLMS_DEFINE_SYSTEM,
)
from ..models import (
    CleanedPatternEntry,
    CleanedPhraseEntry,
    CleanedVocabData,
    CleanedWordEntry,
    ContextSentence,
    PatternOccurrence,
)
from ..models.exam import PatternSubtype
from ..models.sense_assigned import (
    AssignedSense,
    PatternSubtypeData,
    SenseAssignedData,
    SenseAssignedPatternEntry,
    SenseAssignedPhraseEntry,
    SenseAssignedWordEntry,
)
from ..registry import Registry
from ..utils.patterns import (
    get_category_display_name,
    get_subtype_display_name,
    get_subtype_structure,
)

logger = logging.getLogger(__name__)

DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{lemma}"
MAX_CONTEXTS = 6
BATCH_FILTER_SIZE = 10
DICT_MAX_CONCURRENCY = 1  # keep a single in-flight request to avoid hammering free API
DICT_BASE_INTERVAL = 0.6  # start conservative to avoid 429s
DICT_MAX_INTERVAL = 2.5
DICT_MAX_WAIT_ON_429 = 8.0
_dict_semaphore: asyncio.Semaphore | None = None
_dict_rate_lock: asyncio.Lock | None = None
_dict_next_allowed: float = 0.0
_dict_interval: float = DICT_BASE_INTERVAL


class DictionarySense(BaseModel):
    idx: int
    pos: str | None
    definition: str
    example: str | None = None


class SenseCluster(BaseModel):
    primary_id: str = Field(description="Main sense ID representing this cluster (e.g., 's0').")
    merged_ids: list[str] = Field(description="All sense IDs in this cluster, including primary.")
    pos: str = Field(
        description="The part of speech for this cluster (NOUN, VERB, ADJ, ADV, etc.)."
    )
    core_meaning: str = Field(description="Brief description of what this cluster represents.")


class SenseFilterBatchItem(BaseModel):
    lemma: str = Field(description="The lemma as provided in the input XML.")
    clusters: list[SenseCluster] = Field(description="List of 1-4 clustered senses.")


class SenseFilterBatchResponse(BaseModel):
    """Simple wrapper for a list of processed lemmas."""

    items: list[SenseFilterBatchItem]


class LLMSenseCluster(BaseModel):
    pos: str | None = None
    core_meaning: str
    examples: list[str] | None = None


class LLMSenseClusterResponse(BaseModel):
    clusters: list[LLMSenseCluster]


class LLMPhraseSenseCluster(BaseModel):
    core_meaning: str
    examples: list[str] | None = None


class LLMPhraseSenseClusterResponse(BaseModel):
    clusters: list[LLMPhraseSenseCluster]


def _get_dict_semaphore() -> asyncio.Semaphore:
    global _dict_semaphore
    if _dict_semaphore is None:
        _dict_semaphore = asyncio.Semaphore(DICT_MAX_CONCURRENCY)
    return _dict_semaphore


def _get_dict_rate_lock() -> asyncio.Lock:
    global _dict_rate_lock
    if _dict_rate_lock is None:
        _dict_rate_lock = asyncio.Lock()
    return _dict_rate_lock


async def _wait_for_dict_slot() -> None:
    """
    Global throttle to avoid hammering dictionaryapi.dev.
    Enforces a minimum interval between requests plus a small jitter.
    """
    global _dict_next_allowed, _dict_interval
    lock = _get_dict_rate_lock()

    while True:
        async with lock:
            now = asyncio.get_running_loop().time()
            wait_for = _dict_next_allowed - now
            if wait_for <= 0:
                if _dict_interval > 0:
                    jitter = random.uniform(0.01, 0.05)
                    _dict_next_allowed = now + _dict_interval + jitter
                else:
                    _dict_next_allowed = now
                return
        await asyncio.sleep(wait_for)


async def _extend_dict_cooldown(wait_seconds: float) -> None:
    """
    After a 429, extend the global cooldown so other concurrent fetches back off too.
    """
    global _dict_next_allowed, _dict_interval
    lock = _get_dict_rate_lock()
    async with lock:
        now = asyncio.get_running_loop().time()
        cooldown_until = now + min(wait_seconds, DICT_MAX_WAIT_ON_429)
        _dict_interval = min(max(_dict_interval, wait_seconds), DICT_MAX_INTERVAL)
        if cooldown_until > _dict_next_allowed:
            _dict_next_allowed = cooldown_until


def _increase_dict_interval(wait_seconds: float) -> None:
    """
    Raise the pacing interval when we hit a 429 so subsequent requests are slower.
    """
    global _dict_interval
    new_interval = max(_dict_interval * 1.5, wait_seconds, DICT_BASE_INTERVAL)
    new_interval = min(new_interval, DICT_MAX_INTERVAL)
    if new_interval > _dict_interval:
        _dict_interval = new_interval
        logger.warning(f"Dictionary throttle increased to {_dict_interval:.2f}s per request")


def _normalize_pos(pos: str | None) -> str | None:
    if pos is None:
        return None
    mapping = {
        "noun": "NOUN",
        "verb": "VERB",
        "adjective": "ADJ",
        "adverb": "ADV",
        "preposition": "PREP",
        "conjunction": "CONJ",
        "determiner": "DET",
        "interjection": "INTJ",
        "pronoun": "PRON",
    }
    return mapping.get(pos.lower(), pos.upper())


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


async def _fetch_dictionary_senses(lemma: str) -> list[DictionarySense]:
    url = DICTIONARY_API_URL.format(lemma=lemma)
    retries = 4
    resp: httpx.Response | None = None
    semaphore = _get_dict_semaphore()

    for attempt in range(1, retries + 1):
        base_wait = max(_dict_interval, DICT_BASE_INTERVAL)
        async with semaphore:
            await _wait_for_dict_slot()
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    resp = await client.get(url)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Dictionary API request failed for '{lemma}': {e}")
                    if attempt < retries:
                        await asyncio.sleep(base_wait * attempt)
                        continue
                    return []

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            wait_seconds = base_wait * (attempt + 1)
            if retry_after:
                with contextlib.suppress(ValueError):
                    wait_seconds = float(retry_after)
            wait_seconds = max(wait_seconds, _dict_interval * 2)
            if DICT_MAX_WAIT_ON_429:
                wait_seconds = min(wait_seconds, DICT_MAX_WAIT_ON_429)
            logger.warning(
                f"Dictionary API rate limited for '{lemma}' (429). "
                f"Waiting {wait_seconds:.2f}s before retry {attempt}/{retries}."
            )
            _increase_dict_interval(wait_seconds)
            await _extend_dict_cooldown(wait_seconds)
            await asyncio.sleep(wait_seconds)
            continue

        if resp.status_code != 200:
            if resp.status_code != 404:
                logger.warning(f"Dictionary API returned {resp.status_code} for '{lemma}'")
            return []

        break

    if resp is None or resp.status_code != 200:
        return []

    try:
        payload = resp.json()
    except ValueError:
        logger.warning(f"Dictionary API returned invalid JSON for '{lemma}'")
        return []

    senses: list[DictionarySense] = []
    idx = 0

    for entry in payload:
        for meaning in entry.get("meanings", []):
            pos = _normalize_pos(meaning.get("partOfSpeech"))
            for definition in meaning.get("definitions", []):
                def_text = definition.get("definition")
                if not def_text:
                    continue
                senses.append(
                    DictionarySense(
                        idx=idx,
                        pos=pos,
                        definition=def_text.strip(),
                        example=definition.get("example"),
                    )
                )
                idx += 1

    return senses


def _select_contexts(contexts: Sequence[ContextSentence]) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    for ctx in contexts:
        text = ctx.text.strip()
        if text and text not in seen:
            seen.add(text)
            selected.append(text)
        if len(selected) >= MAX_CONTEXTS:
            break
    return selected


def _filter_by_pos(
    senses: list[DictionarySense],
    allowed_pos: list[str],
) -> list[DictionarySense]:
    if not allowed_pos:
        return senses
    allowed = {p.upper() for p in allowed_pos}
    filtered = [s for s in senses if s.pos is None or s.pos in allowed]
    if filtered:
        return filtered

    logger.info("No dictionary senses matched POS %s; keeping unfiltered senses", ",".join(allowed))
    return senses


@dataclass
class DictionaryCandidate:
    entry: CleanedWordEntry | CleanedPhraseEntry
    senses: list[DictionarySense]
    contexts: list[str]
    source_lemma: str


@dataclass
class ClusteredSense:
    primary_sense: DictionarySense
    merged_senses: list[DictionarySense]
    core_meaning: str


def _build_filter_batch_prompt(items: list[DictionaryCandidate]) -> str:
    blocks: list[str] = []
    for item in items:
        senses_block = []
        for s in item.senses:
            example = f"<example>{_escape(s.example)}</example>" if s.example else ""
            pos_attr = f' pos="{s.pos}"' if s.pos else ""
            senses_block.append(
                f'<sense id="s{s.idx}"{pos_attr}>'
                f"<definition>{_escape(s.definition)}</definition>{example}</sense>"
            )

        contexts_block = "\n".join(f"<context>{_escape(c)}</context>" for c in item.contexts)
        blocks.append(
            f'<lemma name="{_escape(item.entry.lemma)}" dict_lemma="{_escape(item.source_lemma)}">\n'
            f"<contexts>\n{contexts_block}\n</contexts>\n"
            f"<senses>\n{chr(10).join(senses_block)}\n</senses>\n"
            f"</lemma>"
        )

    return STAGE3_DICT_FILTER_BATCH_PROMPT.format(lemmas_xml="\n".join(blocks))


def _clusters_to_result(
    clusters: list[SenseCluster],
    senses: list[DictionarySense],
) -> list[ClusteredSense]:
    sense_map = {f"s{s.idx}": s for s in senses}
    result: list[ClusteredSense] = []

    for cluster in clusters:
        primary_id = cluster.primary_id.lower().strip()
        primary = sense_map.get(primary_id)
        if not primary:
            continue

        merged = []
        for mid in cluster.merged_ids:
            mid_clean = mid.lower().strip()
            if mid_clean in sense_map:
                merged.append(sense_map[mid_clean])

        result.append(
            ClusteredSense(
                primary_sense=primary.model_copy(update={"pos": cluster.pos or primary.pos}),
                merged_senses=merged if merged else [primary],
                core_meaning=cluster.core_meaning,
            )
        )

    return result


async def _process_filter_batch(
    batch: list[DictionaryCandidate],
    llm_client: LLMClient,
) -> dict[str, list[ClusteredSense]]:
    prompt = _build_filter_batch_prompt(batch)
    results: dict[str, list[ClusteredSense]] = {}

    try:
        response = await llm_client.complete(
            prompt=prompt,
            system=STAGE3_DICT_FILTER_SYSTEM,
            response_model=SenseFilterBatchResponse,
            tier=ModelTier.BALANCED,
            temperature=0,
        )
        batch_items = getattr(response, "items", None) or getattr(response, "__root__", None)
        if not batch_items:
            raise ValueError("Empty batch filter response")

        cluster_map = {item.lemma.lower(): item.clusters for item in batch_items}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Batch sense clustering failed: {e}")
        return {}

    for candidate in batch:
        lemma_key = candidate.entry.lemma.lower()
        clusters = cluster_map.get(lemma_key)
        if clusters:
            clustered = _clusters_to_result(clusters, candidate.senses)
            if clustered:
                results[lemma_key] = clustered
                continue

        logger.info(f"Dictionary clustering returned empty for '{candidate.entry.lemma}'")

    return results


async def _llm_filter_dictionary_senses_batch(
    items: list[DictionaryCandidate],
    llm_client: LLMClient,
) -> dict[str, list[ClusteredSense]]:
    if not items:
        return {}

    batches = [
        items[i : i + BATCH_FILTER_SIZE] for i in range(0, len(items), BATCH_FILTER_SIZE)
    ]

    batch_results = await asyncio.gather(
        *(_process_filter_batch(batch, llm_client) for batch in batches)
    )

    results: dict[str, list[ClusteredSense]] = {}
    for batch_result in batch_results:
        results.update(batch_result)

    return results


async def _define_senses_with_llm(
    lemma: str,
    contexts: Sequence[ContextSentence],
    pos_hints: list[str],
    llm_client: LLMClient,
) -> list[LLMSenseCluster]:
    contexts_block = "\n".join(
        f"<context>{_escape(ctx.text)}</context>" for ctx in contexts[:MAX_CONTEXTS] if ctx.text
    )
    pos_hint_str = ", ".join(pos_hints) if pos_hints else "unknown"
    prompt = STAGE3_LLMS_DEFINE_PROMPT.format(
        lemma=_escape(lemma),
        pos=pos_hint_str,
        contexts_xml=contexts_block,
    )

    response = await llm_client.complete(
        prompt=prompt,
        system=STAGE3_LLMS_DEFINE_SYSTEM,
        response_model=LLMSenseClusterResponse,
        tier=ModelTier.BALANCED,
        temperature=0.2,
    )
    return response.clusters


async def _define_phrase_senses_with_llm(
    lemma: str,
    contexts: Sequence[ContextSentence],
    llm_client: LLMClient,
) -> list[LLMPhraseSenseCluster]:
    contexts_block = "\n".join(
        f"<context>{_escape(ctx.text)}</context>" for ctx in contexts[:MAX_CONTEXTS] if ctx.text
    )
    prompt = STAGE3_LLMS_DEFINE_PHRASE_PROMPT.format(
        lemma=_escape(lemma),
        contexts_xml=contexts_block,
    )

    response = await llm_client.complete(
        prompt=prompt,
        system=STAGE3_LLMS_DEFINE_SYSTEM,
        response_model=LLMPhraseSenseClusterResponse,
        tier=ModelTier.BALANCED,
        temperature=0.2,
    )
    return response.clusters


def _maybe_adverb_base(lemma: str) -> str | None:
    if lemma.endswith("ally") and len(lemma) > 4:
        return lemma[:-4] + "al"
    if lemma.endswith("ily") and len(lemma) > 3:
        return lemma[:-3] + "y"
    if lemma.endswith("ly") and len(lemma) > 4:
        base = lemma[:-2]
        if base.endswith(("al", "ic", "ous", "ive", "ble", "ful", "less")):
            return base
    return None


async def _prepare_dictionary_candidate(
    entry: CleanedWordEntry | CleanedPhraseEntry,
) -> DictionaryCandidate:
    dict_senses = await _fetch_dictionary_senses(entry.lemma)
    source_lemma = entry.lemma
    if not dict_senses:
        base = _maybe_adverb_base(entry.lemma)
        if base and base != entry.lemma:
            base_senses = await _fetch_dictionary_senses(base)
            if base_senses:
                logger.info(f"Dictionary fallback: '{entry.lemma}' → '{base}'")
                dict_senses = base_senses
                source_lemma = base

    contexts = _select_contexts(entry.contexts)

    return DictionaryCandidate(
        entry=entry, senses=dict_senses, contexts=contexts, source_lemma=source_lemma
    )


async def _register_clustered_senses(
    entry: CleanedWordEntry | CleanedPhraseEntry,
    clustered_senses: list[ClusteredSense],
    registry: Registry,
    source_lemma: str | None = None,
) -> list[AssignedSense]:
    results: list[AssignedSense] = []

    # Phrases should always have pos=None
    is_phrase = isinstance(entry, CleanedPhraseEntry)

    for order, cluster in enumerate(clustered_senses):
        primary = cluster.primary_sense
        pos_value = None if is_phrase else primary.pos

        sense_id = await registry.add_sense(
            lemma=entry.lemma,
            pos=pos_value,
            definition=cluster.core_meaning,
            source="dictionaryapi",
            sense_order=order,
        )

        all_examples = []
        merged_defs = []
        for s in cluster.merged_senses:
            if s.example:
                all_examples.append(s.example)
            merged_defs.append(s.definition)

        results.append(
            AssignedSense(
                sense_id=sense_id,
                source="dictionaryapi",
                pos=pos_value,
                definition=cluster.core_meaning,
                examples=all_examples,
                merged_definitions=merged_defs,
                core_meaning=cluster.core_meaning,
                source_metadata={
                    "primary_index": primary.idx,
                    "merged_indices": [s.idx for s in cluster.merged_senses],
                    **(
                        {"fetched_lemma": source_lemma}
                        if source_lemma and source_lemma != entry.lemma
                        else {}
                    ),
                },
            )
        )

    return results


async def _register_dictionary_senses(
    entry: CleanedWordEntry | CleanedPhraseEntry,
    senses: list[DictionarySense],
    registry: Registry,
    source_lemma: str | None = None,
) -> list[AssignedSense]:
    results: list[AssignedSense] = []

    for order, s in enumerate(senses):
        sense_id = await registry.add_sense(
            lemma=entry.lemma,
            pos=s.pos,
            definition=s.definition,
            source="dictionaryapi",
            sense_order=order,
        )
        results.append(
            AssignedSense(
                sense_id=sense_id,
                source="dictionaryapi",
                pos=s.pos,
                # gloss=s.definition,
                definition=s.definition,
                examples=[s.example] if s.example else [],
                source_metadata={
                    "dictionary_index": s.idx,
                    **(
                        {"fetched_lemma": source_lemma}
                        if source_lemma and source_lemma != entry.lemma
                        else {}
                    ),
                },
            )
        )

    return results


async def _register_llm_senses(
    entry: CleanedWordEntry | CleanedPhraseEntry,
    sense_clusters: list[LLMSenseCluster],
    registry: Registry,
) -> list[AssignedSense]:
    results: list[AssignedSense] = []

    for idx, s in enumerate(sense_clusters):
        sense_id = await registry.add_sense(
            lemma=entry.lemma,
            pos=s.pos,
            definition=s.core_meaning,
            source="llm_generated",
            sense_order=idx,
        )
        results.append(
            AssignedSense(
                sense_id=sense_id,
                source="llm_generated",
                pos=s.pos,
                definition=s.core_meaning,
                examples=s.examples or [],
                source_metadata={"llm_index": idx},
            )
        )

    return results


async def _register_llm_phrase_senses(
    entry: CleanedPhraseEntry,
    sense_clusters: list[LLMPhraseSenseCluster],
    registry: Registry,
) -> list[AssignedSense]:
    results: list[AssignedSense] = []

    for idx, s in enumerate(sense_clusters):
        sense_id = await registry.add_sense(
            lemma=entry.lemma,
            pos=None,
            definition=s.core_meaning,
            source="llm_generated",
            sense_order=idx,
        )
        results.append(
            AssignedSense(
                sense_id=sense_id,
                source="llm_generated",
                pos=None,
                definition=s.core_meaning,
                examples=s.examples or [],
                source_metadata={"llm_index": idx},
            )
        )

    return results


def _load_senses_from_registry(
    entry: CleanedWordEntry | CleanedPhraseEntry,
    registry: Registry,
) -> list[AssignedSense]:
    cached = registry.get_senses_for_lemma(entry.lemma)
    assigned: list[AssignedSense] = []
    for sense in cached:
        source: Literal["dictionaryapi", "llm_generated"] = (
            "dictionaryapi" if sense.source == "dictionaryapi" else "llm_generated"
        )
        assigned.append(
            AssignedSense(
                sense_id=sense.sense_id,
                source=source,
                pos=sense.pos,
                definition=sense.definition,
                examples=[],
            )
        )
    return assigned


def _derive_entry_pos(assigned_senses: list[AssignedSense], fallback_pos: list[str]) -> list[str]:
    pos_values = [s.pos for s in assigned_senses if s.pos]
    if pos_values:
        return sorted({p for p in pos_values})
    return fallback_pos


async def _process_word_entry(
    entry: CleanedWordEntry,
    registry: Registry,
    llm_client: LLMClient,
) -> SenseAssignedWordEntry:
    logger.info(f"Dictionary missing → LLM definitions for '{entry.lemma}'")
    llm_defs = await _define_senses_with_llm(entry.lemma, entry.contexts, entry.pos, llm_client)
    assigned = await _register_llm_senses(entry, llm_defs, registry)
    entry_pos = _derive_entry_pos(assigned, entry.pos)

    return SenseAssignedWordEntry(
        lemma=entry.lemma,
        pos=entry_pos,
        level=entry.level,
        in_official_list=entry.in_official_list,
        frequency=entry.frequency,
        senses=assigned,
        contexts=entry.contexts,
    )


async def _process_phrase_entry(
    entry: CleanedPhraseEntry,
    registry: Registry,
    llm_client: LLMClient,
) -> SenseAssignedPhraseEntry:
    llm_defs = await _define_phrase_senses_with_llm(entry.lemma, entry.contexts, llm_client)
    assigned = await _register_llm_phrase_senses(entry, llm_defs, registry)

    return SenseAssignedPhraseEntry(
        lemma=entry.lemma,
        frequency=entry.frequency,
        senses=assigned,
        contexts=entry.contexts,
    )


def _aggregate_patterns(
    pattern_entries: list[CleanedPatternEntry],
) -> list[SenseAssignedPatternEntry]:
    results = []

    for entry in pattern_entries:
        by_subtype: dict[PatternSubtype | None, list[PatternOccurrence]] = defaultdict(list)
        for occ in entry.occurrences:
            by_subtype[occ.pattern_subtype].append(occ)

        subtypes_data = []

        for subtype, occs in by_subtype.items():
            if subtype is None:
                continue
            subtypes_data.append(
                PatternSubtypeData(
                    subtype=subtype,
                    display_name=get_subtype_display_name(subtype),
                    structure=get_subtype_structure(subtype),
                    occurrences=occs,
                )
            )

        if subtypes_data:
            results.append(
                SenseAssignedPatternEntry(
                    lemma=get_category_display_name(entry.pattern_category),
                    pattern_category=entry.pattern_category,
                    subtypes=subtypes_data,
                )
            )

    return results


async def _process_uncached_entries(
    pending_entries: list[CleanedWordEntry] | list[CleanedPhraseEntry],
    registry: Registry,
    llm_client: LLMClient,
    concurrency: int,
    is_phrase: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
    cached_count: int = 0,
    total_count: int = 0,
) -> list[SenseAssignedWordEntry] | list[SenseAssignedPhraseEntry]:
    """
    Process uncached entries using producer-consumer pattern:
    - Producer: fetch dictionary senses (rate-limited)
    - Consumer: batch LLM calls as candidates accumulate
    """
    if not pending_entries:
        return []

    results: list[SenseAssignedWordEntry] | list[SenseAssignedPhraseEntry] = []
    processed_count = cached_count
    entry_type = "phrase" if is_phrase else "word"
    candidate_queue: asyncio.Queue[DictionaryCandidate | None] = asyncio.Queue()
    llm_fallback_queue: asyncio.Queue[CleanedWordEntry | CleanedPhraseEntry | None] = (
        asyncio.Queue()
    )

    def report_progress():
        nonlocal processed_count
        processed_count += 1
        if progress_callback:
            progress_callback(processed_count, total_count, entry_type)

    async def fetch_producer():
        sem = asyncio.Semaphore(concurrency)

        async def fetch_one(entry):
            async with sem:
                return await _prepare_dictionary_candidate(entry)

        tasks = [fetch_one(e) for e in pending_entries]
        for coro in asyncio.as_completed(tasks):
            candidate = await coro
            await candidate_queue.put(candidate)
        await candidate_queue.put(None)

    async def llm_batch_consumer():
        batch: list[DictionaryCandidate] = []

        while True:
            candidate = await candidate_queue.get()
            if candidate is None:
                if batch:
                    await process_batch(batch)
                await llm_fallback_queue.put(None)
                break

            if candidate.senses:
                batch.append(candidate)
                if len(batch) >= BATCH_FILTER_SIZE:
                    await process_batch(batch)
                    batch = []
            else:
                await llm_fallback_queue.put(candidate.entry)

    async def process_batch(batch: list[DictionaryCandidate]):
        clustered_map = await _llm_filter_dictionary_senses_batch(batch, llm_client)

        for candidate in batch:
            key = candidate.entry.lemma.lower()
            clustered_senses = clustered_map.get(key, [])

            if clustered_senses:
                assigned = await _register_clustered_senses(
                    candidate.entry, clustered_senses, registry, candidate.source_lemma
                )
                if is_phrase:
                    results.append(
                        SenseAssignedPhraseEntry(
                            lemma=candidate.entry.lemma,
                            frequency=candidate.entry.frequency,
                            senses=assigned,
                            contexts=candidate.entry.contexts,
                        )
                    )
                else:
                    entry = candidate.entry
                    entry_pos = _derive_entry_pos(assigned, entry.pos)
                    results.append(
                        SenseAssignedWordEntry(
                            lemma=entry.lemma,
                            pos=entry_pos,
                            level=entry.level,
                            in_official_list=entry.in_official_list,
                            frequency=entry.frequency,
                            senses=assigned,
                            contexts=entry.contexts,
                        )
                    )
                report_progress()
            else:
                await llm_fallback_queue.put(candidate.entry)

    async def llm_fallback_consumer():
        while True:
            entry = await llm_fallback_queue.get()
            if entry is None:
                break

            if is_phrase:
                result = await _process_phrase_entry(entry, registry, llm_client)
                results.append(result)
            else:
                result = await _process_word_entry(entry, registry, llm_client)
                results.append(result)
            report_progress()

    await asyncio.gather(
        fetch_producer(),
        llm_batch_consumer(),
        llm_fallback_consumer(),
    )

    return results


async def assign_all_senses(
    cleaned_data: CleanedVocabData,
    registry: Registry,
    llm_client: LLMClient | None = None,
    concurrency: int = 4,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> SenseAssignedData:
    if llm_client is None:
        llm_client = get_llm_client()

    logger.info(
        f"Stage 3: Dictionary-backed sense inventory for {len(cleaned_data.words)} words "
        f"and {len(cleaned_data.phrases)} phrases"
    )

    word_results: list[SenseAssignedWordEntry] = []
    pending_words: list[CleanedWordEntry] = []
    cached_words = 0
    total_words = len(cleaned_data.words)

    for entry in cleaned_data.words:
        cached_senses = _load_senses_from_registry(entry, registry)
        if cached_senses:
            entry_pos = _derive_entry_pos(cached_senses, entry.pos)
            word_results.append(
                SenseAssignedWordEntry(
                    lemma=entry.lemma,
                    pos=entry_pos,
                    level=entry.level,
                    in_official_list=entry.in_official_list,
                    frequency=entry.frequency,
                    senses=cached_senses,
                    contexts=entry.contexts,
                )
            )
            cached_words += 1
            if progress_callback:
                progress_callback(cached_words, total_words, "word")
        else:
            pending_words.append(entry)

    if pending_words:
        uncached_results = await _process_uncached_entries(
            pending_words,
            registry,
            llm_client,
            concurrency,
            is_phrase=False,
            progress_callback=progress_callback,
            cached_count=cached_words,
            total_count=total_words,
        )
        word_results.extend(uncached_results)

    phrase_results: list[SenseAssignedPhraseEntry] = []
    pending_phrases: list[CleanedPhraseEntry] = []
    cached_phrases = 0
    total_phrases = len(cleaned_data.phrases)

    for entry in cleaned_data.phrases:
        cached_senses = _load_senses_from_registry(entry, registry)
        if cached_senses:
            phrase_results.append(
                SenseAssignedPhraseEntry(
                    lemma=entry.lemma,
                    frequency=entry.frequency,
                    senses=cached_senses,
                    contexts=entry.contexts,
                )
            )
            cached_phrases += 1
            if progress_callback:
                progress_callback(cached_phrases, total_phrases, "phrase")
        else:
            pending_phrases.append(entry)

    if pending_phrases:
        uncached_results = await _process_uncached_entries(
            pending_phrases,
            registry,
            llm_client,
            concurrency,
            is_phrase=True,
            progress_callback=progress_callback,
            cached_count=cached_phrases,
            total_count=total_phrases,
        )
        phrase_results.extend(uncached_results)

    pattern_results = _aggregate_patterns(cleaned_data.patterns)
    if progress_callback and pattern_results:
        progress_callback(len(pattern_results), len(pattern_results), "pattern")

    registry.save()

    total_entries = len(word_results) + len(phrase_results) + len(pattern_results)
    if cached_words or cached_phrases:
        logger.info(
            f"Stage 3 cache: reused {cached_words} words and {cached_phrases} phrases from registry"
        )
    logger.info(f"Stage 3 complete: {total_entries} entries with sense inventory")

    return SenseAssignedData(
        words=word_results,
        phrases=phrase_results,
        patterns=pattern_results,
    )

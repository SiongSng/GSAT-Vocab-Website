import gc
import hashlib
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

import numpy as np
import spacy
import spacy.tokens
import torch
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ..llm import get_llm_client
from ..llm.client import LLMClient, ModelTier
from ..llm.prompts_stage5 import STAGE5_WSD_BATCH_PROMPT, STAGE5_WSD_SYSTEM
from ..models import (
    ContextSentence,
    ExamExample,
    PhraseEntry,
    SenseAssignedData,
    VocabEntry,
    VocabSense,
    WordEntry,
)
from ..registry import Registry
from ..registry.registry import WSD_LLM_VERSION, WSD_MODEL_VERSION
from ..utils import load_spacy_trf

logger = logging.getLogger(__name__)

MODEL_NAME = "ChangeIsKey/graded-wsd"
SPACY_MODEL = "en_core_web_trf"

# graded-wsd outputs scores from 1-4, where higher means better match
# Threshold: if best score is this much higher than second best, we're confident
DIFF_THRESHOLD_CONFIDENT = 0.15

# Thresholds for LLM fallback decision
# Low score + low diff = likely idiom/fixed phrase, ignore
SCORE_THRESHOLD_LOW = 2.5
DIFF_THRESHOLD_IGNORE = 0.05

# Batch size for LLM WSD fallback
WSD_LLM_BATCH_SIZE = 15

# Batch size for graded-wsd model inference
# Smaller batches = more stable memory usage on MPS
WSD_MODEL_BATCH_SIZE = 64

# Batch size for spaCy nlp.pipe()
SPACY_BATCH_SIZE = 64

# Chunk size for processing multi-sense tasks
WSD_CHUNK_SIZE = 200

# Type alias for progress callback: (completed, total, current_lemma) -> None
WSDProgressCallback = Callable[[int, int, str], None]

WSDAction = Literal["assign", "llm", "ignore"]


@dataclass
class WSDTask:
    """A single WSD scoring task: one context sentence for one entry."""

    entry_idx: int
    ctx_idx: int
    lemma: str
    sentence: str
    senses: list[VocabSense]
    cache_key: str = ""
    marked_sentence: str | None = None
    detected_pos: str | None = None
    filtered_senses: list[VocabSense] = field(default_factory=list)
    original_indices: list[int] = field(default_factory=list)


@dataclass
class PendingWSD:
    """A WSD case that needs LLM resolution."""

    lemma: str
    sentence: str
    senses: list[VocabSense]
    original_indices: list[int]
    entry_idx: int
    best_score: float
    score_diff: float


@dataclass
class WSDResult:
    """Result from initial graded-wsd scoring."""

    action: WSDAction
    best_idx: int | None = None
    best_score: float = 0.0
    score_diff: float = 0.0
    filtered_senses: list[VocabSense] = field(default_factory=list)
    original_indices: list[int] = field(default_factory=list)


class WSDItemDecision(BaseModel):
    item_id: int = Field(description="The item ID from input")
    sense_index: int = Field(description="1-based sense index, or 0 if no sense applies (idiom)")


class WSDFallbackResponse(BaseModel):
    items: list[WSDItemDecision]


# POS mapping from spaCy universal tags to our sense POS tags
SPACY_TO_SENSE_POS = {
    "NOUN": "NOUN",
    "VERB": "VERB",
    "ADJ": "ADJ",
    "ADV": "ADV",
    "PROPN": "NOUN",  # proper nouns treated as nouns
    "AUX": "VERB",  # auxiliaries treated as verbs
}


def _get_device() -> str:
    """Determine the best available device for model inference."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _sync_and_clear_gpu() -> None:
    """Synchronize and clear GPU memory."""
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.synchronize()
        torch.mps.empty_cache()
    elif torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.empty_cache()


@lru_cache(maxsize=1)
def _load_spacy_model() -> spacy.Language:
    """Load spaCy model for POS tagging."""
    logger.info(f"Loading spaCy model: {SPACY_MODEL}")
    return load_spacy_trf(SPACY_MODEL)


@lru_cache(maxsize=1)
def _load_model() -> tuple[AutoModelForSequenceClassification, AutoTokenizer]:
    """Load graded-wsd model and tokenizer."""
    device = _get_device()
    logger.info(f"Loading graded-wsd model on device: {device}")

    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.to(device)
    model.eval()

    return model, tokenizer


def load_wsd_model() -> tuple[AutoModelForSequenceClassification, AutoTokenizer]:
    """Load WSD model. Call this explicitly to show download progress."""
    return _load_model()


def _detect_pos_from_doc(doc: spacy.tokens.Doc, lemma: str) -> str | None:
    """Extract POS of a lemma from a pre-parsed spaCy Doc.

    Returns the POS tag (NOUN, VERB, ADJ, ADV) or None if not found.
    """
    lemma_lower = lemma.lower()

    for token in doc:
        if token.lemma_.lower() == lemma_lower or token.text.lower() == lemma_lower:
            return SPACY_TO_SENSE_POS.get(token.pos_)

    return None


def _detect_pos_from_tokens(
    tokens: list[tuple[str, str, str]], lemma: str
) -> str | None:
    """Extract POS of a lemma from cached token info.

    Args:
        tokens: List of (text_lower, lemma_lower, pos) tuples
        lemma: The lemma to find

    Returns the POS tag (NOUN, VERB, ADJ, ADV) or None if not found.
    """
    lemma_lower = lemma.lower()

    for text, token_lemma, pos in tokens:
        if token_lemma == lemma_lower or text == lemma_lower:
            return SPACY_TO_SENSE_POS.get(pos)

    return None


def _filter_senses_by_pos(
    senses: list[VocabSense], detected_pos: str | None
) -> tuple[list[VocabSense], list[int]]:
    """Filter senses to only those matching the detected POS.

    Returns:
        - Filtered list of senses
        - Original indices of the filtered senses (for mapping back)

    If no senses match or POS is None, returns all senses (fallback).
    """
    if detected_pos is None:
        return senses, list(range(len(senses)))

    matching_indices = [i for i, s in enumerate(senses) if s.pos == detected_pos]

    if not matching_indices:
        # Fallback: no matching POS, use all senses
        return senses, list(range(len(senses)))

    return [senses[i] for i in matching_indices], matching_indices


def _mark_target_word(sentence: str, lemma: str) -> str | None:
    """Mark the target word in sentence with <t>...</t> tags.

    Returns None if the lemma is not found in the sentence.
    """
    # Try exact match first (case-insensitive)
    pattern = re.compile(rf"\b({re.escape(lemma)})\b", re.IGNORECASE)
    match = pattern.search(sentence)
    if match:
        return sentence[: match.start(1)] + f"<t>{match.group(1)}</t>" + sentence[match.end(1) :]

    # Try common inflections for verbs
    inflections = [
        lemma + "s",
        lemma + "es",
        lemma + "ed",
        lemma + "ing",
        lemma + "d",
        # Double consonant patterns
        lemma + lemma[-1] + "ed" if lemma[-1] not in "aeiou" else None,
        lemma + lemma[-1] + "ing" if lemma[-1] not in "aeiou" else None,
        # -y to -ies/-ied
        lemma[:-1] + "ies" if lemma.endswith("y") else None,
        lemma[:-1] + "ied" if lemma.endswith("y") else None,
        # -e drop
        lemma[:-1] + "ing" if lemma.endswith("e") else None,
    ]

    for form in inflections:
        if form is None:
            continue
        pattern = re.compile(rf"\b({re.escape(form)})\b", re.IGNORECASE)
        match = pattern.search(sentence)
        if match:
            return (
                sentence[: match.start(1)] + f"<t>{match.group(1)}</t>" + sentence[match.end(1) :]
            )

    return None


def _build_definition_text(sense: VocabSense) -> str:
    """Build definition text for WSD scoring.

    Includes the generated example to help the model better understand the sense.
    Format: "{en_def}. Example: {generated_example}"
    """
    text = sense.en_def
    if sense.generated_example:
        text += f". Example: {sense.generated_example}"
    return text


def _score_senses_batch(
    model: AutoModelForSequenceClassification,
    tokenizer: AutoTokenizer,
    marked_sentences: list[str],
    definitions: list[str],
    device: str,
) -> list[float]:
    """Batch score multiple sentence-definition pairs."""
    if not marked_sentences:
        return []

    input_texts = [
        f"{sent} </s></s> {defn}"
        for sent, defn in zip(marked_sentences, definitions, strict=True)
    ]

    all_scores: list[float] = []
    is_mps = device == "mps"

    for batch_start in range(0, len(input_texts), WSD_MODEL_BATCH_SIZE):
        batch_texts = input_texts[batch_start : batch_start + WSD_MODEL_BATCH_SIZE]

        inputs = tokenizer(  # type: ignore[operator]
            batch_texts,
            truncation=True,
            padding=True,
            max_length=512,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = model(**inputs)  # type: ignore[operator]
            logits = outputs.logits.squeeze(-1)
            if logits.dim() == 0:
                all_scores.append(float(logits.item()))
            else:
                all_scores.extend(logits.tolist())

        # Explicit cleanup after EVERY batch
        del inputs, outputs, logits
        if is_mps:
            torch.mps.synchronize()
            torch.mps.empty_cache()

    gc.collect()
    return all_scores


def _decide_wsd_action(best_score: float, score_diff: float) -> WSDAction:
    """Decide how to handle a WSD case based on graded-wsd scores."""
    if score_diff >= DIFF_THRESHOLD_CONFIDENT:
        return "assign"
    if best_score < SCORE_THRESHOLD_LOW and score_diff < DIFF_THRESHOLD_IGNORE:
        return "ignore"
    return "llm"


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _make_wsd_cache_key(lemma: str, sentence: str, sense_ids: list[str]) -> str:
    """Generate cache key for WSD result based on lemma, sentence, and sense IDs."""
    raw = f"{lemma.lower()}|{sentence}|{','.join(sorted(sense_ids))}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _build_wsd_batch_prompt(items: list[PendingWSD]) -> str:
    """Build XML prompt for batch WSD resolution."""
    blocks: list[str] = []
    for idx, item in enumerate(items):
        senses_xml = "\n".join(
            f'    <sense index="{i + 1}">{_escape_xml(s.zh_def)} - {_escape_xml(s.en_def)}</sense>'
            for i, s in enumerate(item.senses)
        )
        blocks.append(
            f'<item id="{idx}">\n'
            f"  <word>{_escape_xml(item.lemma)}</word>\n"
            f"  <sentence>{_escape_xml(item.sentence)}</sentence>\n"
            f"  <senses>\n{senses_xml}\n  </senses>\n"
            f"</item>"
        )
    return STAGE5_WSD_BATCH_PROMPT.format(items_xml="\n".join(blocks))


@dataclass
class EntryWSDState:
    """Tracks WSD state for a single entry during processing."""

    entry: WordEntry | PhraseEntry
    entry_idx: int
    examples_by_sense: dict[int, list[ExamExample]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.examples_by_sense = {i: [] for i in range(len(self.entry.senses))}


async def perform_wsd(
    sense_data: SenseAssignedData,
    generated_entries: list[VocabEntry],
    progress_callback: WSDProgressCallback | None = None,
    llm_client: LLMClient | None = None,
    registry: Registry | None = None,
) -> list[VocabEntry]:
    """
    Perform Word Sense Disambiguation to assign exam sentences to vocabulary senses.

    Flow:
    1. Single-sense entries: direct assignment (no WSD needed)
    2. Multi-sense entries: check cache first
    3. Cache miss: spaCy POS filtering -> model scoring -> cache result
    4. Low-confidence model results: LLM fallback -> cache result

    Args:
        sense_data: Data containing context sentences for each lemma
        generated_entries: Generated vocabulary entries to update
        progress_callback: Optional callback for progress updates
        llm_client: Optional LLM client for fallback resolution
        registry: Optional registry for WSD result caching

    Returns:
        Updated vocabulary entries with exam examples assigned to senses
    """
    if llm_client is None:
        llm_client = get_llm_client()
    if registry is None:
        registry = Registry()

    contexts_map: dict[str, list[ContextSentence]] = {
        w.lemma.lower(): list(w.contexts) for w in sense_data.words
    }
    for phr in sense_data.phrases:
        contexts_map[phr.lemma.lower()] = list(phr.contexts)

    wsd_entries = [
        (idx, e)
        for idx, e in enumerate(generated_entries)
        if isinstance(e, (WordEntry, PhraseEntry))
    ]

    entry_states: dict[int, EntryWSDState] = {}
    tasks: list[WSDTask] = []
    ctx_source_map: dict[tuple[int, int], ContextSentence] = {}

    single_sense_direct = 0
    for entry_idx, entry in wsd_entries:
        ctxs = contexts_map.get(entry.lemma.lower(), [])
        entry_states[entry_idx] = EntryWSDState(entry=entry, entry_idx=entry_idx)

        if not ctxs:
            continue

        if len(entry.senses) <= 1:
            if entry.senses:
                for ctx in ctxs:
                    entry_states[entry_idx].examples_by_sense[0].append(
                        ExamExample(text=ctx.text, source=ctx.source)
                    )
                    single_sense_direct += 1
            continue

        sense_ids = [s.sense_id for s in entry.senses]
        for ctx_idx, ctx in enumerate(ctxs):
            marked = _mark_target_word(ctx.text, entry.lemma)
            if marked is None:
                continue

            cache_key = _make_wsd_cache_key(entry.lemma, ctx.text, sense_ids)
            tasks.append(
                WSDTask(
                    entry_idx=entry_idx,
                    ctx_idx=ctx_idx,
                    lemma=entry.lemma,
                    sentence=ctx.text,
                    senses=entry.senses,
                    cache_key=cache_key,
                    marked_sentence=marked,
                )
            )
            ctx_source_map[(entry_idx, ctx_idx)] = ctx

    logger.info(f"WSD: {single_sense_direct} contexts from single-sense entries (no WSD needed)")

    if not tasks:
        logger.info("WSD: No multi-sense contexts to process")
        if progress_callback:
            progress_callback(1, 1, "done")
        return _build_updated_entries(generated_entries, entry_states)

    total_tasks = len(tasks)
    all_cache_keys = [t.cache_key for t in tasks]
    cached_results = registry.get_wsd_cache_batch(all_cache_keys)
    del all_cache_keys

    cache_hits = 0
    uncached_tasks: list[WSDTask] = []
    for task in tasks:
        if task.cache_key in cached_results:
            entry = cached_results[task.cache_key]
            ctx = ctx_source_map[(task.entry_idx, task.ctx_idx)]
            state = entry_states[task.entry_idx]
            if entry.sense_idx is not None and 0 <= entry.sense_idx < len(task.senses):
                state.examples_by_sense[entry.sense_idx].append(
                    ExamExample(text=ctx.text, source=ctx.source)
                )
            cache_hits += 1
        else:
            uncached_tasks.append(task)
    del tasks, cached_results

    logger.info(f"WSD: {cache_hits} cache hits, {len(uncached_tasks)} need processing")

    if not uncached_tasks:
        if progress_callback:
            progress_callback(total_tasks, total_tasks, "done")
        return _build_updated_entries(generated_entries, entry_states)

    nlp = _load_spacy_model()

    unique_sentences = list({t.sentence for t in uncached_tasks})
    logger.info(f"WSD: Parsing {len(unique_sentences)} unique sentences")

    pos_cache: dict[str, list[tuple[str, str, str]]] = {}
    for doc, text in zip(
        nlp.pipe(unique_sentences, batch_size=SPACY_BATCH_SIZE), unique_sentences, strict=True
    ):
        pos_cache[text] = [(t.text.lower(), t.lemma_.lower(), t.pos_) for t in doc]
    del unique_sentences

    for task in uncached_tasks:
        tokens = pos_cache[task.sentence]
        task.detected_pos = _detect_pos_from_tokens(tokens, task.lemma)
        task.filtered_senses, task.original_indices = _filter_senses_by_pos(
            task.senses, task.detected_pos
        )
    del pos_cache

    _sync_and_clear_gpu()

    single_sense_tasks: list[WSDTask] = []
    multi_sense_tasks: list[WSDTask] = []
    for task in uncached_tasks:
        if len(task.filtered_senses) == 1:
            single_sense_tasks.append(task)
        else:
            multi_sense_tasks.append(task)
    del uncached_tasks

    cache_to_write: dict[str, tuple[int | None, str, str]] = {}

    # POS filtering reduced to single sense - deterministic, no cache needed
    for task in single_sense_tasks:
        ctx = ctx_source_map[(task.entry_idx, task.ctx_idx)]
        state = entry_states[task.entry_idx]
        sense_idx = task.original_indices[0]
        state.examples_by_sense[sense_idx].append(
            ExamExample(text=ctx.text, source=ctx.source)
        )

    stats = {"assigned": len(single_sense_tasks) + cache_hits, "ignored": 0, "llm_pending": 0}
    del single_sense_tasks

    logger.info(f"WSD: {stats['assigned']} resolved, {len(multi_sense_tasks)} need model scoring")

    # Unload spaCy model to free memory before loading graded-wsd
    _load_spacy_model.cache_clear()
    _sync_and_clear_gpu()

    if not multi_sense_tasks:
        if progress_callback:
            progress_callback(total_tasks, total_tasks, "done")
        return _build_updated_entries(generated_entries, entry_states)

    model, tokenizer = load_wsd_model()
    device = _get_device()

    if progress_callback:
        progress_callback(stats["assigned"], total_tasks, "scoring")

    all_pending: list[PendingWSD] = []
    pending_task_map: dict[int, WSDTask] = {}
    total_cached_written = 0

    processed_tasks = stats["assigned"]
    total_chunks = (len(multi_sense_tasks) + WSD_CHUNK_SIZE - 1) // WSD_CHUNK_SIZE
    logger.info(f"WSD: Starting model scoring ({total_chunks} chunks)")

    for chunk_idx, chunk_start in enumerate(range(0, len(multi_sense_tasks), WSD_CHUNK_SIZE)):
        chunk_tasks = multi_sense_tasks[chunk_start : chunk_start + WSD_CHUNK_SIZE]

        marked_sentences: list[str] = []
        definitions: list[str] = []
        task_score_ranges: list[tuple[int, int]] = []

        for task in chunk_tasks:
            start_idx = len(marked_sentences)
            for sense in task.filtered_senses:
                marked_sentences.append(task.marked_sentence)  # type: ignore[arg-type]
                definitions.append(_build_definition_text(sense))
            task_score_ranges.append((start_idx, len(marked_sentences)))

        all_scores = _score_senses_batch(model, tokenizer, marked_sentences, definitions, device)
        del marked_sentences, definitions

        for local_idx, task in enumerate(chunk_tasks):
            start_idx, end_idx = task_score_ranges[local_idx]
            scores = all_scores[start_idx:end_idx]

            scores_arr = np.array(scores)
            best_filtered_idx = int(np.argmax(scores_arr))
            best_score = float(scores_arr[best_filtered_idx])
            best_original_idx = task.original_indices[best_filtered_idx]

            sorted_scores = np.sort(scores_arr)[::-1]
            score_diff = float(sorted_scores[0] - sorted_scores[1]) if len(scores) > 1 else 0.0

            action = _decide_wsd_action(best_score, score_diff)
            ctx = ctx_source_map[(task.entry_idx, task.ctx_idx)]
            state = entry_states[task.entry_idx]

            if action == "assign":
                state.examples_by_sense[best_original_idx].append(
                    ExamExample(text=ctx.text, source=ctx.source)
                )
                cache_to_write[task.cache_key] = (best_original_idx, "graded_wsd", WSD_MODEL_VERSION)
                stats["assigned"] += 1
            elif action == "ignore":
                cache_to_write[task.cache_key] = (None, "graded_wsd", WSD_MODEL_VERSION)
                stats["ignored"] += 1
            else:
                pending_idx = len(all_pending)
                pending_task_map[pending_idx] = task
                all_pending.append(
                    PendingWSD(
                        lemma=task.lemma,
                        sentence=task.sentence,
                        senses=task.filtered_senses,
                        original_indices=task.original_indices,
                        entry_idx=task.entry_idx,
                        best_score=best_score,
                        score_diff=score_diff,
                    )
                )
                stats["llm_pending"] += 1

        processed_tasks += len(chunk_tasks)
        if progress_callback:
            progress_callback(processed_tasks, total_tasks, f"chunk {chunk_idx + 1}/{total_chunks}")

        # Write cache after each chunk to preserve progress
        if cache_to_write:
            registry.set_wsd_cache_batch(cache_to_write)
            total_cached_written += len(cache_to_write)
            cache_to_write.clear()

        if chunk_idx % 5 == 4:
            _sync_and_clear_gpu()

    del multi_sense_tasks
    _sync_and_clear_gpu()

    if all_pending:
        logger.info(
            f"WSD: {stats['assigned']} assigned, {stats['ignored']} ignored, "
            f"{stats['llm_pending']} pending LLM resolution"
        )
        llm_results = await _resolve_wsd_with_llm_cached(
            all_pending, pending_task_map, llm_client, registry, cache_to_write
        )

        llm_resolved = 0
        llm_idioms = 0
        for pending_idx, sense_idx in llm_results.items():
            task = pending_task_map[pending_idx]
            ctx = ctx_source_map[(task.entry_idx, task.ctx_idx)]
            state = entry_states[task.entry_idx]

            if sense_idx is not None:
                state.examples_by_sense[sense_idx].append(
                    ExamExample(text=ctx.text, source=ctx.source)
                )
                llm_resolved += 1
            else:
                llm_idioms += 1

        logger.info(f"WSD LLM fallback: {llm_resolved} resolved, {llm_idioms} identified as idioms")
    else:
        logger.info(f"WSD: {stats['assigned']} assigned, {stats['ignored']} ignored, no LLM needed")

    if cache_to_write:
        registry.set_wsd_cache_batch(cache_to_write)
        total_cached_written += len(cache_to_write)
    if total_cached_written > 0:
        logger.info(f"WSD: Cached {total_cached_written} new results")

    if progress_callback:
        progress_callback(total_tasks, total_tasks, "done")

    return _build_updated_entries(generated_entries, entry_states)


async def _resolve_wsd_with_llm_cached(
    pending: list[PendingWSD],
    pending_task_map: dict[int, WSDTask],
    llm_client: LLMClient,
    registry: Registry,
    cache_to_write: dict[str, tuple[int | None, str, str]],
) -> dict[int, int | None]:
    """Batch resolve pending WSD cases with LLM and write to cache.

    Returns: {pending_index: chosen_original_sense_index or None if idiom}
    """
    if not pending:
        return {}

    results: dict[int, int | None] = {}
    total_batches = (len(pending) + WSD_LLM_BATCH_SIZE - 1) // WSD_LLM_BATCH_SIZE

    for batch_num, batch_start in enumerate(range(0, len(pending), WSD_LLM_BATCH_SIZE)):
        batch_indices = list(range(batch_start, min(batch_start + WSD_LLM_BATCH_SIZE, len(pending))))
        batch_pending = [pending[i] for i in batch_indices]
        prompt = _build_wsd_batch_prompt(batch_pending)

        if batch_num % 10 == 0:
            logger.info(f"WSD LLM: batch {batch_num + 1}/{total_batches}")

        try:
            response = await llm_client.complete(
                prompt=prompt,
                system=STAGE5_WSD_SYSTEM,
                response_model=WSDFallbackResponse,
                tier=ModelTier.FAST,
                temperature=0,
            )

            for decision in response.items:
                if decision.item_id >= len(batch_indices):
                    continue
                original_idx = batch_indices[decision.item_id]
                item = pending[original_idx]
                task = pending_task_map[original_idx]

                if decision.sense_index == 0:
                    results[original_idx] = None
                    cache_to_write[task.cache_key] = (None, "llm", WSD_LLM_VERSION)
                elif 1 <= decision.sense_index <= len(item.senses):
                    sense_idx = item.original_indices[decision.sense_index - 1]
                    results[original_idx] = sense_idx
                    cache_to_write[task.cache_key] = (sense_idx, "llm", WSD_LLM_VERSION)
                else:
                    logger.warning(
                        f"LLM returned invalid sense_index {decision.sense_index} "
                        f"for '{item.lemma}' (max {len(item.senses)})"
                    )

        except Exception as e:
            logger.warning(f"WSD LLM batch {batch_num + 1} failed: {e}")

        # Write cache periodically during LLM phase
        if batch_num % 20 == 19 and cache_to_write:
            registry.set_wsd_cache_batch(cache_to_write)
            cache_to_write.clear()

    return results


def _build_updated_entries(
    generated_entries: list[VocabEntry],
    entry_states: dict[int, EntryWSDState],
) -> list[VocabEntry]:
    """Build final entries with examples assigned to senses."""
    updated_entries: list[VocabEntry] = list(generated_entries)

    for entry_idx, state in entry_states.items():
        updated_senses = []
        for idx, sense in enumerate(state.entry.senses):
            examples = list(sense.examples) if sense.examples else []
            examples.extend(state.examples_by_sense.get(idx, []))
            updated_senses.append(sense.model_copy(update={"examples": examples}))

        updated_entry = state.entry.model_copy(update={"senses": updated_senses})
        updated_entries[entry_idx] = updated_entry

    return updated_entries

import asyncio
import hashlib
import logging
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from ..llm import get_llm_client
from ..llm.client import LLMClient, ModelTier
from ..llm.prompts_stage4 import (
    STAGE4_PATTERN_CATEGORY_PROMPT,
    STAGE4_PATTERN_CATEGORY_SYSTEM,
    STAGE4_PATTERN_SUBTYPE_PROMPT,
    STAGE4_PATTERN_SUBTYPE_SYSTEM,
    STAGE4_SENSE_GENERATE_PROMPT,
    STAGE4_SENSE_GENERATE_SYSTEM,
)
from ..models import (
    ConfusionNote,
    ExamExample,
    PatternEntry,
    PatternSubtypeOutput,
    PhraseEntry,
    RootInfo,
    SenseAssignedData,
    SenseAssignedPatternEntry,
    SenseAssignedPhraseEntry,
    SenseAssignedWordEntry,
    VocabEntry,
    VocabSense,
    WordEntry,
)
from ..registry import Registry
from ..utils import (
    get_category_display_name,
    get_subtype_display_name,
    get_subtype_structure,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def _chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


class GeneratedSenseDefinition(BaseModel):
    sense_index: int
    zh_def: str
    en_def: str
    generated_example: str


class GeneratedConfusionNote(BaseModel):
    confused_with: str
    distinction: str
    memory_tip: str


class GeneratedRootInfo(BaseModel):
    root_breakdown: str | None = None
    memory_strategy: str


class BatchSenseGenerateResponse(BaseModel):
    words: list["WordSenseGeneration"]


class WordSenseGeneration(BaseModel):
    lemma: str
    senses: list[GeneratedSenseDefinition]
    confusion_notes: list[GeneratedConfusionNote] | None = None
    root_info: GeneratedRootInfo | None = None


class PatternCategoryGeneration(BaseModel):
    teaching_explanation: str


class PatternSubtypeGeneration(BaseModel):
    generated_example: str


def _base_definition(sense) -> str:
    return (sense.definition or "").strip()


def _make_generation_cache_key(entry: SenseAssignedWordEntry | SenseAssignedPhraseEntry) -> str:
    parts: list[str] = []
    for sense in entry.senses:
        parts.append(f"{sense.sense_id}|{sense.pos or 'NONE'}|{_base_definition(sense)}")
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _escape(s: str) -> str:
    from xml.sax.saxutils import escape

    return escape(s, {'"': "&quot;"})


def _normalize_lemma(lemma: str) -> str:
    import re

    normalized = lemma.lower().strip()
    normalized = re.sub(r"\s+'s\b", "'s", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _build_sense_batch_prompt(
    entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry],
) -> str:
    lines = ["<words>"]

    for entry in entries:
        is_word = isinstance(entry, SenseAssignedWordEntry)

        lemma = _escape(entry.lemma)
        entry_type = "word" if is_word else "phrase"
        level = entry.level if isinstance(entry, SenseAssignedWordEntry) else "unknown"
        pos = ",".join(entry.pos) if isinstance(entry, SenseAssignedWordEntry) else ""

        lines.append(f'  <word lemma="{lemma}" type="{entry_type}" level="{level}" pos="{pos}">')

        contexts = [ctx.text for ctx in getattr(entry, "contexts", [])[:4]]
        if contexts:
            lines.append("    <contexts>")
            for ctx in contexts:
                lines.append(f"      <context>{_escape(ctx)}</context>")
            lines.append("    </contexts>")

        for i, sense in enumerate(entry.senses):
            sense_pos = sense.pos or "UNKNOWN"
            base_def = _base_definition(sense)
            source = sense.source
            examples = "; ".join(sense.examples[:2]) if sense.examples else ""
            merged_defs = getattr(sense, "merged_definitions", [])
            core_meaning = getattr(sense, "core_meaning", None)

            lines.append(f'    <sense index="{i}" pos="{sense_pos}" source="{source}">')
            if core_meaning:
                lines.append(f"      <core_meaning>{_escape(core_meaning)}</core_meaning>")
            if base_def:
                lines.append(f"      <base_definition>{_escape(base_def)}</base_definition>")
            if merged_defs:
                merged_text = "; ".join(merged_defs[:3])
                lines.append(
                    f"      <merged_definitions>{_escape(merged_text)}</merged_definitions>"
                )
            if examples:
                lines.append(f"      <source_examples>{_escape(examples)}</source_examples>")
            lines.append("    </sense>")

        lines.append("  </word>")

    lines.append("</words>")
    return "\n".join(lines)


async def _generate_senses_batch(
    entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry],
    llm_client: LLMClient | None = None,
) -> dict[str, WordSenseGeneration]:
    client = llm_client or get_llm_client()
    prompt = STAGE4_SENSE_GENERATE_PROMPT.format(words_xml=_build_sense_batch_prompt(entries))
    total_senses = sum(len(entry.senses) for entry in entries)
    logger.debug(
        "Stage 4: generating %d entries (%d senses), prompt chars=%d",
        len(entries),
        total_senses,
        len(prompt),
    )

    try:
        response = await client.complete(
            prompt=prompt,
            system=STAGE4_SENSE_GENERATE_SYSTEM,
            response_model=BatchSenseGenerateResponse,
            temperature=0.2,
            tier=ModelTier.FAST,
        )
    except Exception as e:
        logger.error(f"Batch sense generation failed: {e}")
        return {}

    result = {}
    for word_gen in response.words:
        result[_normalize_lemma(word_gen.lemma)] = word_gen

    return result


async def _generate_senses_with_retry(
    entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry],
    llm_client: LLMClient,
    *,
    max_attempts: int = 3,
    batch_size: int = BATCH_SIZE,
    retry_delay: float = 2.0,
) -> tuple[dict[str, WordSenseGeneration], list[SenseAssignedWordEntry | SenseAssignedPhraseEntry]]:
    aggregated: dict[str, WordSenseGeneration] = {}
    pending = list(entries)
    attempt = 1

    while pending and attempt <= max_attempts:
        if attempt > 1:
            delay = retry_delay * (2 ** (attempt - 2))
            logger.info(f"Stage 4: retry attempt {attempt}, waiting {delay:.1f}s...")
            await asyncio.sleep(delay)

        chunks = list(_chunked(pending, batch_size))
        chunk_results = await asyncio.gather(
            *(_generate_senses_batch(chunk, llm_client) for chunk in chunks)
        )
        round_results: dict[str, WordSenseGeneration] = {}
        for result in chunk_results:
            round_results.update(result)

        aggregated.update(round_results)
        pending = [e for e in entries if _normalize_lemma(e.lemma) not in aggregated]

        if pending and attempt < max_attempts:
            lemma_preview = ", ".join(e.lemma for e in pending[:5])
            logger.warning(
                f"Stage 4: missing generation for {len(pending)} entries after attempt {attempt}: {lemma_preview}"
            )

        attempt += 1

    return aggregated, pending


def _load_cached_generation(
    entry: SenseAssignedWordEntry | SenseAssignedPhraseEntry,
    cache_key: str,
    registry: Registry,
) -> WordSenseGeneration | None:
    payload = registry.get_generation_cache(entry.lemma, cache_key)
    if not payload:
        return None

    try:
        cached = WordSenseGeneration.model_validate_json(payload)
        return cached
    except ValidationError as e:
        logger.warning(f"Invalid cache for '{entry.lemma}', regenerating: {e}")
        return None


def _store_generation_cache(
    entry: SenseAssignedWordEntry | SenseAssignedPhraseEntry,
    cache_key: str,
    generation: WordSenseGeneration,
    registry: Registry,
) -> None:
    registry.upsert_generation_cache(
        entry.lemma,
        cache_key,
        generation.model_dump_json(),
    )


async def _generate_pattern_category_explanation(
    entry: SenseAssignedPatternEntry,
) -> str:
    client = get_llm_client()
    category_display = get_category_display_name(entry.pattern_category)

    prompt = STAGE4_PATTERN_CATEGORY_PROMPT.format(
        category=entry.pattern_category.value,
        display_name=category_display,
    )

    try:
        response = await client.complete(
            prompt=prompt,
            system=STAGE4_PATTERN_CATEGORY_SYSTEM,
            response_model=PatternCategoryGeneration,
            temperature=0.3,
            tier=ModelTier.SMART,
        )
        return response.teaching_explanation
    except Exception as e:
        logger.error(f"Pattern category generation failed for {entry.lemma}: {e}")
        return f"{category_display}的語法說明"


async def _generate_pattern_subtype_example(
    lemma: str,
    subtype_data,
) -> str:
    client = get_llm_client()
    display_name = get_subtype_display_name(subtype_data.subtype)
    structure = get_subtype_structure(subtype_data.subtype)

    contexts = [occ.sentence for occ in subtype_data.occurrences[:3]]
    contexts_xml = "\n".join([f"    <context>{_escape(ctx)}</context>" for ctx in contexts])

    prompt = STAGE4_PATTERN_SUBTYPE_PROMPT.format(
        subtype=subtype_data.subtype.value,
        display_name=display_name,
        structure=structure,
        contexts=contexts_xml,
    )

    try:
        response = await client.complete(
            prompt=prompt,
            system=STAGE4_PATTERN_SUBTYPE_SYSTEM,
            response_model=PatternSubtypeGeneration,
            temperature=0.3,
            tier=ModelTier.SMART,
        )
        return response.generated_example
    except Exception as e:
        logger.error(f"Pattern subtype generation failed for {lemma}: {e}")
        return f"Example sentence for {structure}"


def _resolve_sense_to_example_assignments(
    entry: SenseAssignedWordEntry | SenseAssignedPhraseEntry,
    generated: WordSenseGeneration,
) -> dict[int, list[int]]:
    """
    Map generated sense indices to assigned sense indices using embeddings.
    Returns: {generated_idx: [assigned_sense_indices]}
    """
    if len(generated.senses) == len(entry.senses):
        return {i: [i] for i in range(len(generated.senses))}

    return {i: [i] for i in range(min(len(generated.senses), len(entry.senses)))}


def _build_vocab_entry_from_generation(
    entry: SenseAssignedWordEntry | SenseAssignedPhraseEntry,
    generated: WordSenseGeneration,
) -> VocabEntry:
    vocab_senses: list[VocabSense] = []

    sorted_gen_senses = sorted(generated.senses, key=lambda s: s.sense_index)
    for gen_sense in sorted_gen_senses:
        if gen_sense.sense_index >= len(entry.senses):
            logger.warning(
                f"{entry.lemma}: generated sense_index {gen_sense.sense_index} out of range"
            )
            continue

        assigned_sense = entry.senses[gen_sense.sense_index]
        examples: list[ExamExample] = []

        vocab_senses.append(
            VocabSense(
                sense_id=assigned_sense.sense_id,
                pos=assigned_sense.pos,
                zh_def=gen_sense.zh_def,
                en_def=gen_sense.en_def,
                examples=examples,
                generated_example=gen_sense.generated_example,
            )
        )

    confusion_notes = []
    if generated.confusion_notes:
        confusion_notes = [
            ConfusionNote(
                confused_with=note.confused_with,
                distinction=note.distinction,
                memory_tip=note.memory_tip,
            )
            for note in generated.confusion_notes
        ]

    if isinstance(entry, SenseAssignedWordEntry):
        root_info = None
        if generated.root_info:
            root_info = RootInfo(
                root_breakdown=generated.root_info.root_breakdown,
                memory_strategy=generated.root_info.memory_strategy,
            )

        return WordEntry(
            lemma=entry.lemma,
            pos=entry.pos,
            level=entry.level,
            in_official_list=entry.in_official_list,
            frequency=entry.frequency,
            senses=vocab_senses,
            confusion_notes=confusion_notes,
            root_info=root_info,
        )

    return PhraseEntry(
        lemma=entry.lemma,
        frequency=entry.frequency,
        senses=vocab_senses,
        confusion_notes=confusion_notes,
    )


async def _process_word_phrase_batch(
    entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry],
    registry: Registry,
    llm_client: LLMClient | None = None,
) -> tuple[dict[str, WordSenseGeneration], list[SenseAssignedWordEntry | SenseAssignedPhraseEntry]]:
    llm_client = llm_client or get_llm_client()

    cache_hits: dict[str, WordSenseGeneration] = {}
    to_generate: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry] = []
    cache_keys: dict[str, str] = {}

    for entry in entries:
        cache_key = _make_generation_cache_key(entry)
        normalized_key = _normalize_lemma(entry.lemma)
        cache_keys[normalized_key] = cache_key
        cached = _load_cached_generation(entry, cache_key, registry)
        if cached:
            cache_hits[normalized_key] = cached
        else:
            to_generate.append(entry)

    generated_map: dict[str, WordSenseGeneration] = {}
    if to_generate:
        generated_map = await _generate_senses_batch(to_generate, llm_client)
        for entry in to_generate:
            normalized_key = _normalize_lemma(entry.lemma)
            gen = generated_map.get(normalized_key)
            if gen:
                _store_generation_cache(entry, cache_keys[normalized_key], gen, registry)

    missing_entries = [entry for entry in to_generate if _normalize_lemma(entry.lemma) not in generated_map]

    final_map = {**cache_hits, **generated_map}
    return final_map, missing_entries


async def _process_pattern_entry(entry: SenseAssignedPatternEntry) -> PatternEntry:
    teaching_explanation = await _generate_pattern_category_explanation(entry)

    subtype_examples = await asyncio.gather(
        *(_generate_pattern_subtype_example(entry.lemma, sd) for sd in entry.subtypes)
    )

    subtype_outputs: list[PatternSubtypeOutput] = []
    for subtype_data, generated_example in zip(entry.subtypes, subtype_examples, strict=True):
        examples = [
            ExamExample(text=occ.sentence, source=occ.source) for occ in subtype_data.occurrences
        ]

        subtype_outputs.append(
            PatternSubtypeOutput(
                subtype=subtype_data.subtype,
                display_name=subtype_data.display_name,
                structure=subtype_data.structure,
                examples=examples,
                generated_example=generated_example,
            )
        )

    return PatternEntry(
        lemma=entry.lemma,
        pattern_category=entry.pattern_category,
        subtypes=subtype_outputs,
        teaching_explanation=teaching_explanation,
    )


async def generate_all_entries(
    sense_assigned_data: SenseAssignedData,
    registry: Registry | None = None,
    progress_callback: Callable[[int, int, str, int, int, int], None] | None = None,
) -> list[VocabEntry]:
    registry = registry or Registry()
    llm_client = get_llm_client()
    word_phrase_entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry] = []
    word_phrase_entries.extend(sense_assigned_data.words)
    word_phrase_entries.extend(sense_assigned_data.phrases)
    pattern_entries = sense_assigned_data.patterns

    all_batches: list[list[SenseAssignedWordEntry | SenseAssignedPhraseEntry]] = []
    for i in range(0, len(word_phrase_entries), BATCH_SIZE):
        batch = word_phrase_entries[i : i + BATCH_SIZE]
        all_batches.append(batch)

    total_batches = len(all_batches)
    logger.info(
        f"Stage 4: {len(word_phrase_entries)} word/phrase entries → {total_batches} batches"
    )

    batch_results = await asyncio.gather(
        *(_process_word_phrase_batch(batch, registry, llm_client) for batch in all_batches)
    )

    generation_map: dict[str, WordSenseGeneration] = {}
    retry_entries: list[SenseAssignedWordEntry | SenseAssignedPhraseEntry] = []

    for idx, (batch_map, batch_missing) in enumerate(batch_results):
        generation_map.update(batch_map)
        retry_entries.extend(batch_missing)

        if progress_callback:
            progress_callback(
                idx + 1,
                len(all_batches),
                "word_phrase",
                len(generation_map),
                min((idx + 1) * BATCH_SIZE, len(word_phrase_entries)),
                len(word_phrase_entries),
            )

    if retry_entries:
        generated_map, missing_entries = await _generate_senses_with_retry(
            retry_entries, llm_client
        )

        for entry in retry_entries:
            normalized_key = _normalize_lemma(entry.lemma)
            gen = generated_map.get(normalized_key)
            if not gen:
                continue

            generation_map[normalized_key] = gen
            cache_key = _make_generation_cache_key(entry)
            _store_generation_cache(entry, cache_key, gen, registry)

        if missing_entries:
            preview = ", ".join(e.lemma for e in missing_entries[:5])
            logger.warning(
                f"Stage 4: generation failed after retry for {len(missing_entries)} entries (skipping): {preview}"
            )

    all_results: list[VocabEntry] = []
    for entry in word_phrase_entries:
        normalized_key = _normalize_lemma(entry.lemma)
        generated = generation_map.get(normalized_key)
        if not generated:
            logger.warning(f"Stage 4: skipping '{entry.lemma}' - no generation available")
            continue
        all_results.append(_build_vocab_entry_from_generation(entry, generated))

    logger.info(f"Stage 4: Processing {len(pattern_entries)} pattern entries")
    pattern_tasks = [_process_pattern_entry(e) for e in pattern_entries]
    pattern_results = await asyncio.gather(*pattern_tasks)
    all_results.extend(pattern_results)

    total_input = (
        len(sense_assigned_data.words)
        + len(sense_assigned_data.phrases)
        + len(sense_assigned_data.patterns)
    )
    logger.info(f"Stage 4 complete: {total_input} input → {len(all_results)} generated")

    return all_results

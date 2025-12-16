import asyncio
import contextlib
import logging
from collections.abc import Callable, Sequence
from typing import Literal
from xml.sax.saxutils import escape

import numpy as np
from pydantic import BaseModel

from ..llm import get_llm_client
from ..llm.client import ModelTier
from ..llm.prompts import STAGE3_GENERATE_SYSTEM
from ..models import (
    AnnotationRole,
    CleanedPatternEntry,
    CleanedPhraseEntry,
    CleanedVocabData,
    CleanedVocabEntry,
    CleanedWordEntry,
    ConfusionNote,
    ExamExample,
    FrequencyData,
    LemmaOccurrence,
    PhraseEntry,
    RootInfo,
    VocabEntry,
    VocabSense,
    WordEntry,
)

logger = logging.getLogger(__name__)


class GeneratedSense(BaseModel):
    pos: (
        Literal[
            "NOUN",
            "VERB",
            "ADJ",
            "ADV",
            "PRON",
            "DET",
            "CONJ",
            "PREP",
            "AUX",
            "OTHER",
        ]
        | None
    ) = None
    zh_def: str
    en_def: str
    example: str


class GeneratedConfusionNote(BaseModel):
    confused_with: str
    distinction: str
    memory_tip: str


class GeneratedRootInfo(BaseModel):
    root_breakdown: str | None = None
    memory_strategy: str


class GeneratedPatternInfo(BaseModel):
    pattern_type: Literal[
        "conditional",
        "subjunctive",
        "relative_clause",
        "passive_voice",
        "inversion",
        "cleft_sentence",
        "participle_construction",
        "emphatic",
        "other",
    ]
    display_name: str | None
    structure: str


class GeneratedItem(BaseModel):
    lemma: str
    senses: list[GeneratedSense]
    confusion_notes: list[GeneratedConfusionNote] | None = None
    root_info: GeneratedRootInfo | None = None
    pattern_info: GeneratedPatternInfo | None = None


class GeneratedBatchResponse(BaseModel):
    items: list[GeneratedItem]


def _normalize_pos_tag(pos: str) -> str:
    p = pos.strip().upper()
    mapping = {"ADJECTIVE": "ADJ", "ADVERB": "ADV"}
    return mapping.get(p, p)


def _pos_to_sense_id_abbrev(pos: str) -> str:
    abbrev_map = {
        "NOUN": "n",
        "VERB": "v",
        "ADJ": "adj",
        "ADV": "adv",
        "PHRASE": "phr",
        "PRON": "pron",
        "DET": "det",
        "CONJ": "conj",
        "PREP": "prep",
        "AUX": "aux",
        "OTHER": "x",
    }
    return abbrev_map.get(pos.upper(), "x")


def _build_distractor_map_from_entries(
    entries: list[CleanedVocabEntry],
) -> dict[str, set[str]]:
    distractor_map: dict[str, set[str]] = {}
    for entry in entries:
        if isinstance(entry, CleanedPatternEntry):
            continue
        for occ in entry.occurrences:
            if occ.source.role in (AnnotationRole.CORRECT_ANSWER, AnnotationRole.DISTRACTOR):
                distractor_map.setdefault(entry.lemma.lower(), set())
    return distractor_map


def _escape(s: str) -> str:
    return escape(s, {'"': "&quot;"})


def _build_word_block(
    entry: CleanedWordEntry | CleanedPhraseEntry, distractor_map: dict[str, set[str]] | None = None
) -> str:
    entry_type = entry.type.value if hasattr(entry.type, "value") else entry.type
    lvl = "unknown"
    pos = ""

    if isinstance(entry, CleanedWordEntry):
        lvl = entry.level if entry.level is not None else "unknown"
        pos = ",".join(entry.pos) if entry.pos else ""

    lines = [
        f'<entry lemma="{_escape(entry.lemma)}" type="{entry_type}" level="{lvl}" pos="{pos}">'
    ]

    if isinstance(entry, CleanedWordEntry) and entry.frequency.tested_count > 0 and distractor_map:
        related = distractor_map.get(entry.lemma.lower(), set())
        if related:
            short_related = [d for d in related if len(d) < 50]
            if short_related:
                lines.append(f"  <distractors>{', '.join(list(short_related)[:6])}</distractors>")

    lines.append("</entry>")
    return "\n".join(lines)


def _build_prompt(
    entries: Sequence[CleanedWordEntry | CleanedPhraseEntry],
    distractor_map: dict[str, set[str]] | None = None,
) -> str:
    blocks = [_build_word_block(e, distractor_map) for e in entries]
    return "<entries>\n" + "\n".join(blocks) + "\n</entries>"


def _convert_item(
    entry: CleanedWordEntry | CleanedPhraseEntry,
    item: GeneratedItem,
    example_assignments: dict[int, list[ExamExample]],
) -> VocabEntry:
    pos_counter: dict[str, int] = {}
    senses = []
    is_phrase = isinstance(entry, CleanedPhraseEntry)

    for i, s in enumerate(item.senses):
        sense_pos = s.pos if s.pos else ("PHRASE" if is_phrase else "OTHER")
        normalized_pos = _normalize_pos_tag(sense_pos)
        pos_counter[normalized_pos] = pos_counter.get(normalized_pos, 0) + 1
        pos_abbrev = _pos_to_sense_id_abbrev(normalized_pos)
        sense_id = (
            f"{entry.lemma.lower().replace(' ', '_')}_{pos_abbrev}_{pos_counter[normalized_pos]}"
        )

        sense_examples = example_assignments.get(i, [])

        senses.append(
            VocabSense(
                sense_id=sense_id,
                pos=normalized_pos if not is_phrase else None,
                zh_def=s.zh_def,
                en_def=s.en_def,
                examples=sense_examples,
                generated_example=s.example,
            )
        )

    confusion_notes = []
    if item.confusion_notes:
        confusion_notes = [
            ConfusionNote(
                confused_with=c.confused_with,
                distinction=c.distinction,
                memory_tip=c.memory_tip,
            )
            for c in item.confusion_notes
        ]

    if isinstance(entry, CleanedWordEntry):
        root_info = None
        if entry.level and entry.level >= 2 and item.root_info:
            root_info = RootInfo(
                root_breakdown=item.root_info.root_breakdown,
                memory_strategy=item.root_info.memory_strategy,
            )

        pos_set = {p.upper() for p in entry.pos} if entry.pos else set()
        for s in senses:
            if s.pos:
                pos_set.add(s.pos)

        valid_word_pos = {p for p in pos_set if p not in ("PHRASE",)}
        final_pos = sorted(valid_word_pos) if valid_word_pos else []

        return WordEntry(
            lemma=entry.lemma,
            pos=final_pos,
            level=entry.level,
            in_official_list=entry.in_official_list,
            senses=senses,
            frequency=entry.frequency,
            confusion_notes=confusion_notes,
            root_info=root_info,
        )

    elif isinstance(entry, CleanedPhraseEntry):
        return PhraseEntry(
            lemma=entry.lemma,
            senses=senses,
            frequency=entry.frequency,
            confusion_notes=confusion_notes,
        )

    else:
        return WordEntry(
            lemma=entry.lemma,
            pos=[],
            level=None,
            in_official_list=False,
            senses=senses,
            frequency=entry.frequency,
            confusion_notes=confusion_notes,
        )


def _fallback_assign_by_pos(
    assignments: dict[str, dict[int, list[ExamExample]]],
    lemma: str,
    item: GeneratedItem,
    senses_by_pos: dict[str, list[int]],
    examples_by_pos: dict[str, list[tuple[int, ExamExample]]],
    unknown_examples: list[tuple[int, ExamExample]],
) -> None:
    for pos, ex_list in examples_by_pos.items():
        sense_indices = senses_by_pos.get(pos, [])
        if sense_indices:
            target_idx = sense_indices[0]
            for _, ex in ex_list:
                assignments[lemma][target_idx].append(ex)
        elif item.senses:
            assignments[lemma][0].extend([ex for _, ex in ex_list])

    if unknown_examples and item.senses:
        for _, ex in unknown_examples:
            assignments[lemma][0].append(ex)


async def _resolve_polysemy(
    entries: list[CleanedWordEntry | CleanedPhraseEntry], items: list[GeneratedItem]
) -> dict[str, dict[int, list[ExamExample]]]:
    entry_map = {e.lemma.lower(): e for e in entries}
    assignments: dict[str, dict[int, list[ExamExample]]] = {}

    texts_to_embed: list[str] = []
    # (kind, lemma, idx) where kind is "sense" or "example"
    text_indices: list[tuple[str, str, int]] = []
    tasks_to_resolve = []

    for item in items:
        lemma_key = item.lemma.lower()
        entry = entry_map.get(lemma_key)
        if not entry:
            continue

        assignments[lemma_key] = {i: [] for i in range(len(item.senses))}

        # Group senses and examples by POS
        senses_by_pos = {}  # normalized_pos -> list of sense indices
        for i, s in enumerate(item.senses):
            sense_pos = s.pos if s.pos else "PHRASE"
            norm_pos = _normalize_pos_tag(sense_pos)
            senses_by_pos.setdefault(norm_pos, []).append(i)

        examples_by_pos = {}  # normalized_pos -> list of (example_idx, ExamExample)
        unknown_pos_examples = []  # list of (example_idx, ExamExample)
        all_examples = [
            ExamExample(text=occ.sentence, source=occ.source) for occ in entry.occurrences
        ]

        for j, occ in enumerate(entry.occurrences):
            norm_pos = _normalize_pos_tag(occ.pos)
            ex = all_examples[j]
            if norm_pos == "UNKNOWN":
                unknown_pos_examples.append((j, ex))
            else:
                examples_by_pos.setdefault(norm_pos, []).append((j, ex))

        # Check if we need embedding-based resolution
        needs_embedding = False
        if unknown_pos_examples:
            needs_embedding = True
        for pos in examples_by_pos:
            if len(senses_by_pos.get(pos, [])) > 1:
                needs_embedding = True
                break

        if needs_embedding:
            ambiguous_pos_set = set()
            for pos in examples_by_pos:
                if len(senses_by_pos.get(pos, [])) > 1:
                    ambiguous_pos_set.add(pos)

            senses_to_embed = set()
            examples_to_embed = set()

            for pos in ambiguous_pos_set:
                for si in senses_by_pos.get(pos, []):
                    senses_to_embed.add(si)
                for ex_idx, _ in examples_by_pos.get(pos, []):
                    examples_to_embed.add(ex_idx)

            if unknown_pos_examples:
                for si in range(len(item.senses)):
                    senses_to_embed.add(si)
                for ex_idx, _ in unknown_pos_examples:
                    examples_to_embed.add(ex_idx)

            tasks_to_resolve.append(
                (
                    lemma_key,
                    item,
                    senses_by_pos,
                    examples_by_pos,
                    unknown_pos_examples,
                    all_examples,
                    senses_to_embed,
                    examples_to_embed,
                )
            )

            for i in senses_to_embed:
                s = item.senses[i]
                text = f"{s.zh_def} {s.en_def}"
                texts_to_embed.append(text)
                text_indices.append(("sense", lemma_key, i))

            for j in examples_to_embed:
                ex = all_examples[j]
                texts_to_embed.append(ex.text)
                text_indices.append(("example", lemma_key, j))
        else:
            for pos, ex_list in examples_by_pos.items():
                sense_indices = senses_by_pos.get(pos, [])
                if sense_indices:
                    target_idx = sense_indices[0]
                    for _, ex in ex_list:
                        assignments[lemma_key][target_idx].append(ex)
                elif item.senses:
                    assignments[lemma_key][0].extend([ex for _, ex in ex_list])

    if not texts_to_embed:
        return assignments

    # Batch Embed
    client = get_llm_client()
    embeddings_list = None
    with contextlib.suppress(Exception):
        embeddings_list = await client.get_embeddings(texts_to_embed)

    if not embeddings_list:
        for (
            lemma,
            item,
            senses_by_pos,
            examples_by_pos,
            unknown_examples,
            _all_examples,
            _senses_to_embed,
            _examples_to_embed,
        ) in tasks_to_resolve:
            _fallback_assign_by_pos(
                assignments, lemma, item, senses_by_pos, examples_by_pos, unknown_examples
            )
        return assignments

    emb_map = {}
    for i, emb in enumerate(embeddings_list):
        kind, lemma, idx = text_indices[i]
        if lemma not in emb_map:
            emb_map[lemma] = {"senses": {}, "examples": {}}
        emb_map[lemma][f"{kind}s"][idx] = np.array(emb)

    for (
        lemma,
        item,
        senses_by_pos,
        examples_by_pos,
        unknown_examples,
        _all_examples,
        _senses_to_embed,
        _examples_to_embed,
    ) in tasks_to_resolve:
        lemma_embs = emb_map.get(lemma)
        if not lemma_embs:
            _fallback_assign_by_pos(
                assignments, lemma, item, senses_by_pos, examples_by_pos, unknown_examples
            )
            continue

        sense_vecs = lemma_embs["senses"]
        ex_vecs = lemma_embs["examples"]

        for pos, ex_list in examples_by_pos.items():
            sense_indices = senses_by_pos.get(pos, [])
            if not sense_indices:
                if item.senses:
                    assignments[lemma][0].extend([ex for _, ex in ex_list])
                continue

            if len(sense_indices) == 1:
                idx = sense_indices[0]
                assignments[lemma][idx].extend([ex for _, ex in ex_list])
            else:
                candidate_vecs = [sense_vecs.get(si) for si in sense_indices]
                if all(v is not None for v in candidate_vecs):
                    for ex_idx, ex in ex_list:
                        ex_vec = ex_vecs.get(ex_idx)
                        if ex_vec is not None:
                            scores = [np.dot(ex_vec, sv) for sv in candidate_vecs]
                            best_local_idx = int(np.argmax(scores))
                            best_sense_idx = sense_indices[best_local_idx]
                            assignments[lemma][best_sense_idx].append(ex)
                        else:
                            assignments[lemma][sense_indices[0]].append(ex)
                else:
                    for _, ex in ex_list:
                        assignments[lemma][sense_indices[0]].append(ex)

        if unknown_examples:
            all_sense_indices = list(range(len(item.senses)))
            candidate_vecs = [sense_vecs.get(si) for si in all_sense_indices]
            if all(v is not None for v in candidate_vecs):
                for ex_idx, ex in unknown_examples:
                    ex_vec = ex_vecs.get(ex_idx)
                    if ex_vec is not None:
                        scores = [np.dot(ex_vec, sv) for sv in candidate_vecs]
                        best_idx = int(np.argmax(scores))
                        assignments[lemma][best_idx].append(ex)
                    elif item.senses:
                        assignments[lemma][0].append(ex)
            elif item.senses:
                for _, ex in unknown_examples:
                    assignments[lemma][0].append(ex)

    return assignments


async def _generate_batch(
    entries: list[CleanedWordEntry | CleanedPhraseEntry],
    distractor_map: dict[str, set[str]] | None = None,
):
    client = get_llm_client()
    prompt = _build_prompt(entries, distractor_map)
    response = await client.complete(
        prompt=prompt,
        system=STAGE3_GENERATE_SYSTEM,
        response_model=GeneratedBatchResponse,
        temperature=0.3,
        tier=ModelTier.SMART,
    )
    entry_map = {e.lemma.lower(): e for e in entries}
    results: list[VocabEntry] = []
    matched_lemmas = set()

    if not response.items:
        logger.error(
            f"Batch returned EMPTY items! {len(entries)} entries lost: {[e.lemma for e in entries[:10]]}..."
        )
        return results

    assignments = await _resolve_polysemy(entries, response.items)

    for item in response.items:
        entry = entry_map.get(item.lemma.lower())
        if entry:
            matched_lemmas.add(item.lemma.lower())
            if type(entry) is CleanedWordEntry and entry.level == 1:
                item.root_info = None
            if type(entry) is CleanedWordEntry and entry.frequency.tested_count == 0:
                item.confusion_notes = None
            results.append(_convert_item(entry, item, assignments.get(entry.lemma.lower(), {})))

    unmatched = set(entry_map.keys()) - matched_lemmas
    if unmatched:
        logger.warning(
            f"Batch: {len(entries)} input, {len(response.items)} returned, {len(results)} matched, {len(unmatched)} unmatched: {list(unmatched)[:5]}..."
        )

    return results


BATCH_SIZE = 35


def _create_batches(
    entries: list[CleanedWordEntry | CleanedPhraseEntry],
    entry_type: str,
    distractor_map: dict[str, set[str]] | None,
) -> list[list[CleanedWordEntry | CleanedPhraseEntry]]:
    batches: list[list[CleanedWordEntry | CleanedPhraseEntry]] = []
    for i in range(0, len(entries), BATCH_SIZE):
        batches.append(entries[i : i + BATCH_SIZE])
    return batches


async def generate_all_entries(
    cleaned_data: CleanedVocabData,
    debug_first_batch: bool = False,
    progress_callback: Callable | None = None,
) -> list[VocabEntry]:
    distractor_map = _build_distractor_map_from_entries(cleaned_data.entries)

    existing_lemmas = {e.lemma.lower() for e in cleaned_data.entries}
    essay_entries = []
    seen_essay_words = set()

    for topic in cleaned_data.essay_topics:
        for word in topic.suggested_words:
            w_lower = word.lower().strip()
            if w_lower and w_lower not in existing_lemmas and w_lower not in seen_essay_words:
                seen_essay_words.add(w_lower)
                essay_entries.append(
                    CleanedWordEntry(
                        lemma=word,
                        level=None,
                        in_official_list=False,
                        pos=[],
                        occurrences=[
                            LemmaOccurrence(
                                pos="UNKNOWN",
                                surface=word,
                                sentence=f"Essay Topic: {topic.description[:100]}...",
                                source=topic.source,
                            )
                        ],
                        frequency=FrequencyData(
                            total_occurrences=0,
                            tested_count=0,
                            year_spread=0,
                            ml_score=None,
                        ),
                    )
                )

    word_entries: list[CleanedWordEntry] = [
        e for e in cleaned_data.entries if isinstance(e, CleanedWordEntry)
    ]
    phrase_entries: list[CleanedPhraseEntry] = [
        e for e in cleaned_data.entries if isinstance(e, CleanedPhraseEntry)
    ]

    all_processable: list[CleanedWordEntry | CleanedPhraseEntry] = (
        word_entries + phrase_entries + essay_entries
    )

    all_batches: list[tuple[str, list[CleanedWordEntry | CleanedPhraseEntry]]] = []

    tested_entries: list[CleanedWordEntry | CleanedPhraseEntry] = [
        e
        for e in all_processable
        if isinstance(e, CleanedWordEntry) and e.frequency.tested_count > 0
    ]
    other_entries: list[CleanedWordEntry | CleanedPhraseEntry] = [
        e
        for e in all_processable
        if not (isinstance(e, CleanedWordEntry) and e.frequency.tested_count > 0)
    ]

    if tested_entries:
        batches = _create_batches(tested_entries, "tested", distractor_map)
        logger.info(f"  tested: {len(tested_entries)} entries → {len(batches)} batches")
        if debug_first_batch:
            batches = batches[:1]
        for batch in batches:
            all_batches.append(("tested", batch))

    if other_entries and not debug_first_batch:
        batches = _create_batches(other_entries, "other", None)
        logger.info(f"  other: {len(other_entries)} entries → {len(batches)} batches")
        for batch in batches:
            all_batches.append(("other", batch))

    total_batches = len(all_batches)
    total_input_entries = sum(len(batch) for _, batch in all_batches)
    logger.info(f"Stage 3: {total_input_entries} entries → {total_batches} batches")

    completed_count = 0
    total_generated = 0
    total_processed = 0
    all_missing: list[str] = []
    lock = asyncio.Lock()

    async def process_batch(
        idx: int, entry_type: str, batch: list[CleanedWordEntry | CleanedPhraseEntry]
    ) -> list[VocabEntry]:
        nonlocal completed_count, total_generated, total_processed
        batch_lemmas = {e.lemma.lower() for e in batch}
        try:
            dm = distractor_map if entry_type == "tested" else None
            res = await _generate_batch(batch, dm)
        except Exception as e:
            logger.error(f"Batch {idx} FAILED ({entry_type}, {len(batch)} entries): {e}")
            res = []

        generated_lemmas = {e.lemma.lower() for e in res}
        missing = batch_lemmas - generated_lemmas

        async with lock:
            completed_count += 1
            total_generated += len(res)
            total_processed += len(batch)
            if missing:
                all_missing.extend(missing)
            if progress_callback:
                progress_callback(
                    completed_count,
                    total_batches,
                    entry_type,
                    total_generated,
                    total_processed,
                    total_input_entries,
                )
        return res

    tasks = [
        process_batch(i, entry_type, batch) for i, (entry_type, batch) in enumerate(all_batches)
    ]
    results = await asyncio.gather(*tasks)

    all_results: list[VocabEntry] = []
    for res in results:
        all_results.extend(res)

    if all_missing:
        logger.warning(f"Missing {len(all_missing)} entries: {all_missing[:20]}...")
    logger.info(f"Stage 3 complete: {total_input_entries} input → {len(all_results)} generated")

    all_results.sort(
        key=lambda e: (e.frequency.tested_count, e.frequency.total_occurrences), reverse=True
    )
    return all_results

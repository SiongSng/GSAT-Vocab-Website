import logging
from collections import defaultdict

import nltk
from nltk.corpus import wordnet as wn

from ..models import VocabEntry

logger = logging.getLogger(__name__)

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

MAX_RELATIONS = 5

POS_MAP = {
    "NOUN": wn.NOUN,
    "VERB": wn.VERB,
    "ADJ": wn.ADJ,
    "ADV": wn.ADV,
}


def _get_wordnet_relations(lemma: str, pos_list: list[str]) -> tuple[set[str], set[str], set[str]]:
    synonyms = set()
    antonyms = set()
    derived = set()

    for pos in pos_list:
        wn_pos = POS_MAP.get(pos.upper())
        if not wn_pos:
            continue

        for synset in wn.synsets(lemma, pos=wn_pos):
            for syn_lemma in synset.lemmas():
                name = syn_lemma.name().replace("_", " ").lower()
                if name != lemma.lower():
                    synonyms.add(name)

                for ant in syn_lemma.antonyms():
                    ant_name = ant.name().replace("_", " ").lower()
                    antonyms.add(ant_name)

                for form in syn_lemma.derivationally_related_forms():
                    form_name = form.name().replace("_", " ").lower()
                    if form_name != lemma.lower():
                        derived.add(form_name)

    return synonyms, antonyms, derived


def compute_relations(
    entries: list[VocabEntry],
    progress_callback: callable = None,
) -> list[VocabEntry]:
    if not entries:
        return entries

    lemma_set = {e.lemma.lower() for e in entries}
    total = len(entries)

    synonyms_map: dict[str, list[str]] = defaultdict(list)
    antonyms_map: dict[str, list[str]] = defaultdict(list)
    derived_map: dict[str, list[str]] = defaultdict(list)

    for i, entry in enumerate(entries):
        if entry.type != "word":
            continue

        syns, ants, dervs = _get_wordnet_relations(entry.lemma, entry.pos or [])

        filtered_syns = [s for s in syns if s in lemma_set][:MAX_RELATIONS]
        filtered_ants = [a for a in ants if a in lemma_set][:MAX_RELATIONS]
        filtered_dervs = [d for d in dervs if d in lemma_set][:MAX_RELATIONS]

        if filtered_syns:
            synonyms_map[entry.lemma] = filtered_syns
        if filtered_ants:
            antonyms_map[entry.lemma] = filtered_ants
        if filtered_dervs:
            derived_map[entry.lemma] = filtered_dervs

        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total, i + 1)

    if progress_callback:
        progress_callback(total, total, total)

    updated_entries: list[VocabEntry] = []
    for entry in entries:
        syns = synonyms_map.get(entry.lemma)
        ants = antonyms_map.get(entry.lemma)
        dervs = derived_map.get(entry.lemma)

        updated = entry.model_copy(
            update={
                "synonyms": syns if syns else None,
                "antonyms": ants if ants else None,
                "derived_forms": dervs if dervs else None,
            }
        )
        updated_entries.append(updated)

    syn_count = sum(1 for e in updated_entries if e.synonyms)
    ant_count = sum(1 for e in updated_entries if e.antonyms)
    derv_count = sum(1 for e in updated_entries if e.derived_forms)
    logger.info(
        f"Found {syn_count} entries with synonyms, {ant_count} with antonyms, {derv_count} with derived forms"
    )

    return updated_entries

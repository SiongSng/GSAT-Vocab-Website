import logging
import re
from collections import defaultdict

import spacy

from ..models import (
    AnnotationRole,
    AnnotationType,
    CleanedPatternEntry,
    CleanedPhraseEntry,
    CleanedVocabData,
    CleanedWordEntry,
    EssayTopicData,
    FrequencyData,
    LemmaOccurrence,
    OfficialWordEntry,
    PatternOccurrence,
    SectionType,
    SentenceRole,
    SourceInfo,
    StructuredExam,
    is_tested,
)

logger = logging.getLogger(__name__)

STOP_POS = {
    "ADP",
    "AUX",
    "CONJ",
    "CCONJ",
    "DET",
    "NUM",
    "PART",
    "PRON",
    "SCONJ",
    "PUNCT",
    "SPACE",
    "SYM",
    "X",
    "PROPN",
}

POS_NORMALIZE = {
    "N.": "NOUN",
    "NOUN": "NOUN",
    "V.": "VERB",
    "VERB": "VERB",
    "ADJ.": "ADJ",
    "ADJ": "ADJ",
    "ADJECTIVE": "ADJ",
    "ADV.": "ADV",
    "ADV": "ADV",
    "ADVERB": "ADV",
    "PREP.": "PREP",
    "PREP": "PREP",
    "CONJ.": "CONJ",
    "CONJ": "CONJ",
    "PRON.": "PRON",
    "PRON": "PRON",
    "ART.": "ART",
    "ART": "ART",
    "AUX.": "AUX",
    "AUX": "AUX",
}

_nlp = None


def _normalize_pos(pos: str) -> str:
    return POS_NORMALIZE.get(pos.upper(), pos.upper())


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return _nlp


def _build_official_lemma_set(wordlist: dict[str, OfficialWordEntry]) -> set[str]:
    nlp = get_nlp()
    lemma_set = set()
    for word in wordlist:
        lemma_set.add(word.lower())
        doc = nlp(word)
        for token in doc:
            lemma_set.add(token.lemma_.lower())
    return lemma_set


def _check_in_official(lemma: str, official_lemmas: set[str]) -> bool:
    return lemma.lower() in official_lemmas


def normalize_phrase(phrase: str, nlp) -> str:
    doc = nlp(phrase)
    result = []

    for token in doc:
        if token.pos_ == "AUX":
            continue
        if token.pos_ == "VERB":
            result.append(token.lemma_.lower())
        else:
            result.append(token.text.lower())

    return " ".join(result)


def _calculate_frequency(occurrences: list[LemmaOccurrence]) -> FrequencyData:
    total = len(occurrences)
    tested = sum(1 for o in occurrences if is_tested(o.source))
    years = {o.source.year for o in occurrences}

    return FrequencyData(
        total_occurrences=total,
        tested_count=tested,
        year_spread=len(years),
        ml_score=None,
    )


def _calculate_pattern_frequency(occurrences: list[PatternOccurrence]) -> FrequencyData:
    total = len(occurrences)
    tested = sum(1 for o in occurrences if is_tested(o.source))
    years = {o.source.year for o in occurrences}

    return FrequencyData(
        total_occurrences=total,
        tested_count=tested,
        year_spread=len(years),
        ml_score=None,
    )


def _is_valid_surface(surface: str, sentence: str) -> bool:
    if re.search(r"^[\w\s]+:", surface) or re.search(r"\w+/\w+-clause", surface, re.IGNORECASE):
        return False

    surface_lower = surface.lower()
    sentence_lower = sentence.lower()

    if surface_lower in sentence_lower:
        return True

    def normalize(s: str) -> str:
        s = s.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        s = re.sub(r"[.,!?;:]+", "", s)
        return s

    if normalize(surface_lower) in normalize(sentence_lower):
        return True

    if "..." in surface_lower or "…" in surface_lower:
        parts = re.split(r"\.{2,}|…", surface_lower)
        parts = [p.strip() for p in parts if p.strip()]
        if all(p in sentence_lower for p in parts):
            return True

    return True


def _find_annotation_role(
    token_surface: str, token_lemma: str, annotations: list
) -> AnnotationRole | None:
    surface_lower = token_surface.lower()
    lemma_lower = token_lemma.lower()

    for annotation in annotations:
        ann_surface_lower = annotation.surface.lower()
        if surface_lower == ann_surface_lower or lemma_lower == ann_surface_lower:
            return annotation.role
        if surface_lower in ann_surface_lower or ann_surface_lower in surface_lower:
            return annotation.role
    return None


def _process_sections(
    exams: list[StructuredExam],
    nlp,
) -> tuple[
    dict[str, list[LemmaOccurrence]],
    dict[str, list[LemmaOccurrence]],
    dict[str, list[PatternOccurrence]],
]:
    lemma_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)
    phrase_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)
    pattern_map: dict[str, list[PatternOccurrence]] = defaultdict(list)

    for exam in exams:
        for section in exam.sections:
            for sentence in section.sentences:
                base_source = SourceInfo(
                    year=exam.year,
                    exam_type=exam.exam_type,
                    section_type=section.type,
                    question_number=sentence.question,
                    sentence_role=sentence.sentence_role,
                )

                annotations = sentence.annotations or []

                for ann in annotations:
                    source = base_source.model_copy(update={"role": ann.role})

                    if ann.type == AnnotationType.PATTERN:
                        if ann.pattern_category is None:
                            logger.warning(
                                f"Pattern annotation missing category: '{ann.surface}' "
                                f"(year={exam.year}, q={sentence.question})"
                            )
                            continue

                        pattern_key = f"{ann.pattern_category.value}"
                        pattern_map[pattern_key].append(
                            PatternOccurrence(
                                pattern_category=ann.pattern_category,
                                pattern_subtype=ann.pattern_subtype,
                                surface=ann.surface,
                                sentence=sentence.text,
                                source=source,
                            )
                        )

                    elif ann.type == AnnotationType.PHRASE:
                        if not _is_valid_surface(ann.surface, sentence.text):
                            logger.warning(
                                f"Skipping invalid phrase: surface '{ann.surface}' "
                                f"not found in sentence (year={exam.year}, q={sentence.question})"
                            )
                            continue

                        normalized = normalize_phrase(ann.surface, nlp)
                        phrase_map[normalized].append(
                            LemmaOccurrence(
                                pos="PHRASE",
                                surface=ann.surface,
                                sentence=sentence.text,
                                source=source,
                            )
                        )

                    elif ann.type == AnnotationType.WORD:
                        doc = nlp(ann.surface)
                        for token in doc:
                            if not token.is_alpha or len(token.lemma_) <= 1:
                                continue
                            lemma = token.lemma_.lower()
                            lemma_map[lemma].append(
                                LemmaOccurrence(
                                    pos=token.pos_,
                                    surface=ann.surface,
                                    sentence=sentence.text,
                                    source=source,
                                )
                            )

                if sentence.sentence_role == SentenceRole.QUESTION_PROMPT:
                    continue

                doc = nlp(sentence.text)
                for sent in doc.sents:
                    sent_text = sent.text.strip()
                    for token in sent:
                        if token.pos_ in STOP_POS:
                            continue
                        if not token.is_alpha:
                            continue
                        if token.is_stop:
                            continue
                        if len(token.lemma_) <= 1:
                            continue

                        role = _find_annotation_role(token.text, token.lemma_, annotations)
                        if role is not None:
                            continue

                        source = base_source.model_copy(update={"role": None})
                        lemma = token.lemma_.lower()
                        lemma_map[lemma].append(
                            LemmaOccurrence(
                                pos=token.pos_,
                                surface=token.text,
                                sentence=sent_text,
                                source=source,
                            )
                        )

    return lemma_map, phrase_map, pattern_map


def _process_translation_items(
    exams: list[StructuredExam],
    nlp,
) -> dict[str, list[LemmaOccurrence]]:
    lemma_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)

    for exam in exams:
        for item in exam.translation_items:
            source_info = SourceInfo(
                year=exam.year,
                exam_type=exam.exam_type,
                section_type=SectionType.TRANSLATION,
                question_number=item.question,
                role=AnnotationRole.TESTED_KEYWORD,
                sentence_role=None,
            )

            for keyword in item.keywords:
                doc = nlp(keyword)
                for token in doc:
                    if not token.is_alpha or len(token.lemma_) <= 1:
                        continue
                    if token.pos_ in STOP_POS:
                        continue

                    lemma = token.lemma_.lower()
                    lemma_map[lemma].append(
                        LemmaOccurrence(
                            pos=token.pos_,
                            surface=keyword,
                            sentence=item.chinese_prompt,
                            source=source_info,
                        )
                    )

    return lemma_map


def _dedupe_occurrences(occurrences: list[LemmaOccurrence]) -> list[LemmaOccurrence]:
    seen = set()
    result = []
    for occ in occurrences:
        if re.search(r"__\d+__", occ.sentence):
            continue
        key = (occ.sentence.strip(), occ.source.year, occ.source.question_number)
        if key not in seen:
            seen.add(key)
            result.append(occ)
    return result


def _dedupe_pattern_occurrences(occurrences: list[PatternOccurrence]) -> list[PatternOccurrence]:
    seen = set()
    result = []
    for occ in occurrences:
        key = (
            occ.sentence.strip(),
            occ.source.year,
            occ.source.question_number,
            occ.pattern_subtype,
        )
        if key not in seen:
            seen.add(key)
            result.append(occ)
    return result


def clean_and_aggregate(
    exams: list[StructuredExam],
    official_wordlist: dict[str, OfficialWordEntry],
) -> CleanedVocabData:
    nlp = get_nlp()
    official_lemmas = _build_official_lemma_set(official_wordlist)

    sentence_lemmas, phrase_lemmas, pattern_map = _process_sections(exams, nlp)
    translation_lemmas = _process_translation_items(exams, nlp)

    essay_topics = []
    for exam in exams:
        for topic in exam.essay_topics:
            essay_topics.append(
                EssayTopicData(
                    description=topic.description,
                    suggested_words=topic.suggested_words,
                    source=SourceInfo(
                        year=exam.year,
                        exam_type=exam.exam_type,
                        section_type=SectionType.MIXED,
                        question_number=None,
                    ),
                )
            )

    all_lemmas: dict[str, list[LemmaOccurrence]] = defaultdict(list)
    for lemma, occs in sentence_lemmas.items():
        all_lemmas[lemma].extend(occs)
    for lemma, occs in translation_lemmas.items():
        all_lemmas[lemma].extend(occs)

    for word in official_wordlist:
        if word not in all_lemmas:
            all_lemmas[word] = []

    entries = []

    for lemma, occurrences in all_lemmas.items():
        occurrences = _dedupe_occurrences(occurrences)

        official = official_wordlist.get(lemma)
        in_official = _check_in_official(lemma, official_lemmas)
        level = int(official.level) if official and official.level.isdigit() else None

        if occurrences:
            frequency = _calculate_frequency(occurrences)
            pos = sorted({_normalize_pos(o.pos) for o in occurrences})
        else:
            frequency = FrequencyData(
                total_occurrences=0,
                tested_count=0,
                year_spread=0,
                ml_score=None,
            )
            pos = [_normalize_pos(p) for p in official.parts_of_speech] if official else []

        valid_pos = {"NOUN", "VERB", "ADJ", "ADV"}
        pos = [p for p in pos if p in valid_pos]
        if not pos:
            continue

        entries.append(
            CleanedWordEntry(
                lemma=lemma,
                level=level,
                in_official_list=in_official,
                pos=pos,
                occurrences=occurrences,
                frequency=frequency,
            )
        )

    for phrase, occurrences in phrase_lemmas.items():
        occurrences = _dedupe_occurrences(occurrences)
        if not occurrences:
            continue

        frequency = _calculate_frequency(occurrences)

        entries.append(
            CleanedPhraseEntry(
                lemma=phrase,
                occurrences=occurrences,
                frequency=frequency,
            )
        )

    for category_key, occurrences in pattern_map.items():
        occurrences = _dedupe_pattern_occurrences(occurrences)
        if not occurrences:
            continue

        pattern_category = occurrences[0].pattern_category
        frequency = _calculate_pattern_frequency(occurrences)

        entries.append(
            CleanedPatternEntry(
                lemma=pattern_category.value,
                pattern_category=pattern_category,
                occurrences=occurrences,
                frequency=frequency,
            )
        )

    entries.sort(
        key=lambda e: (e.frequency.tested_count, e.frequency.total_occurrences), reverse=True
    )

    return CleanedVocabData(
        entries=entries,
        essay_topics=essay_topics,
    )


def clean_and_classify(
    exams: list[StructuredExam],
    official_wordlist: dict[str, OfficialWordEntry],
) -> CleanedVocabData:
    return clean_and_aggregate(exams, official_wordlist)

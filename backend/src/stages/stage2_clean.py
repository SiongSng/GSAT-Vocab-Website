import logging
import math
import re
from collections import defaultdict
from datetime import datetime

import spacy

from ..models import (
    AnnotationRole,
    CleanedVocabData,
    CleanedVocabEntry,
    DistractorGroup,
    EssayTopicData,
    ExamType,
    FrequencyData,
    LemmaOccurrence,
    OfficialWordEntry,
    SectionType,
    SentenceRole,
    SourceInfo,
    StructuredExam,
    TranslationItem,
    VocabTier,
)

logger = logging.getLogger(__name__)

CURRICULUM_CUTOFF_YEAR = 111
TRIAL_YEARS = {110, 111}

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


def _normalize_pos(pos: str) -> str:
    return POS_NORMALIZE.get(pos.upper(), pos.upper())


_nlp = None


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


ROLE_WEIGHTS = {
    AnnotationRole.CORRECT_ANSWER: 1.0,
    AnnotationRole.DISTRACTOR: 0.4,
    AnnotationRole.TESTED_KEYWORD: 1.2,
    AnnotationRole.NOTABLE_PATTERN: 0.7,
    AnnotationRole.NOTABLE_PHRASE: 0.5,
}

SECTION_WEIGHTS = {
    SectionType.READING: 1.8,
    SectionType.STRUCTURE: 1.2,
    SectionType.VOCABULARY: 1.0,
    SectionType.DISCOURSE: 0.9,
    SectionType.MIXED: 1.0,
    SectionType.CLOZE: 0.5,
}

EXAM_WEIGHTS = {
    ExamType.GSAT: 1.2,
    ExamType.GSAT_REF: 1.1,
    ExamType.GSAT_MAKEUP: 1.0,
    ExamType.GSAT_TRIAL: 1.1,
    ExamType.AST: 0.6,
    ExamType.AST_MAKEUP: 0.5,
}

SENTENCE_ROLE_WEIGHTS = {
    SentenceRole.CLOZE: 1.0,
    SentenceRole.PASSAGE: 0.6,
    SentenceRole.QUESTION_PROMPT: 0.2,
    SentenceRole.OPTION: 0.8,
    SentenceRole.UNUSED_OPTION: 0.5,
}

OFFICIAL_BONUS_COEFFICIENT = 0.54
YEAR_SPREAD_COEFFICIENT = 0.05
RECENCY_COEFFICIENT = 0.04
DISTRACTOR_PARTNER_COEFFICIENT = 0.02
PRE_CURRICULUM_MULTIPLIER = 1.12
POST_CURRICULUM_MULTIPLIER = 0.90
TRIAL_PERIOD_MULTIPLIER = 1.05


def _calculate_time_decay(year: int, current_year: int | None = None, half_life: int = 10) -> float:
    if current_year is None:
        current_year = datetime.now().year - 1911
    delta = max(0, current_year - year)

    if delta <= 3:
        return 1.0

    weight = math.pow(0.5, (delta - 3) / half_life)
    return round(weight, 3)


def _calculate_frequency(
    occurrences: list[LemmaOccurrence],
    in_official: bool = False,
    level: int | None = None,
    distractor_partner_count: int = 0,
) -> FrequencyData:
    total = len(occurrences)
    tested = sum(
        1
        for o in occurrences
        if o.role
        in (
            AnnotationRole.CORRECT_ANSWER,
            AnnotationRole.TESTED_KEYWORD,
            AnnotationRole.DISTRACTOR,
        )
    )
    years = {o.source.year for o in occurrences}
    year_spread = len(years)

    current_year = datetime.now().year - 1911

    pre_108_score = 0.0
    post_108_score = 0.0

    for occ in occurrences:
        r_w = ROLE_WEIGHTS.get(occ.role, 1.0)
        s_w = SECTION_WEIGHTS.get(occ.source.section_type, 1.0)
        t_w = _calculate_time_decay(occ.source.year, current_year)
        e_w = EXAM_WEIGHTS.get(occ.source.exam_type, 1.0)

        item_score = r_w * s_w * t_w * e_w

        if occ.source.year < CURRICULUM_CUTOFF_YEAR:
            pre_108_score += item_score * PRE_CURRICULUM_MULTIPLIER
        elif occ.source.year in TRIAL_YEARS:
            post_108_score += item_score * TRIAL_PERIOD_MULTIPLIER
        else:
            post_108_score += item_score * POST_CURRICULUM_MULTIPLIER

    base_score = math.log2(1 + pre_108_score + post_108_score)

    official_bonus = 1.0 + OFFICIAL_BONUS_COEFFICIENT * (1 if in_official else 0)

    spread_bonus = 1.0 + YEAR_SPREAD_COEFFICIENT * min(year_spread, 10)

    recent_years = {y for y in years if current_year - y <= 3}
    recency_bonus = 1.0 + RECENCY_COEFFICIENT * len(recent_years)

    distractor_bonus = 1.0 + DISTRACTOR_PARTNER_COEFFICIENT * min(distractor_partner_count, 10)

    final_score = base_score * official_bonus * spread_bonus * recency_bonus * distractor_bonus

    return FrequencyData(
        total_occurrences=total,
        tested_count=tested,
        year_spread=year_spread,
        weighted_score=round(final_score, 2),
    )


def _determine_tier(occurrences: list[LemmaOccurrence], in_official: bool) -> VocabTier:
    roles = {o.role for o in occurrences}

    if AnnotationRole.CORRECT_ANSWER in roles or AnnotationRole.DISTRACTOR in roles:
        return VocabTier.TESTED
    if AnnotationRole.TESTED_KEYWORD in roles:
        return VocabTier.TRANSLATION
    if AnnotationRole.NOTABLE_PATTERN in roles:
        return VocabTier.PATTERN
    if AnnotationRole.NOTABLE_PHRASE in roles:
        return VocabTier.PHRASE

    return VocabTier.BASIC


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


def _process_sentences(
    exams: list[StructuredExam],
) -> tuple[
    dict[str, list[LemmaOccurrence]], dict[str, list[LemmaOccurrence]], list[DistractorGroup]
]:
    nlp = get_nlp()
    lemma_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)
    phrase_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)
    distractor_groups: list[DistractorGroup] = []

    for exam in exams:
        for section in exam.sections:
            for sentence in section.sentences:
                sentence_source = SourceInfo(
                    year=exam.year,
                    exam_type=exam.exam_type,
                    section_type=section.type,
                    question_number=sentence.question,
                )

                annotations = sentence.annotations or []

                correct_answers = [
                    a.surface for a in annotations if a.role == AnnotationRole.CORRECT_ANSWER
                ]
                distractors = [
                    a.surface for a in annotations if a.role == AnnotationRole.DISTRACTOR
                ]

                if correct_answers and distractors:
                    for correct in correct_answers:
                        distractor_groups.append(
                            DistractorGroup(
                                correct_answer=correct,
                                distractors=distractors,
                                question_context=sentence.text,
                                source=sentence_source,
                            )
                        )

                for ann in annotations:
                    if ann.type in ("phrase", "pattern"):
                        if not _is_valid_surface(ann.surface, sentence.text):
                            logger.warning(
                                f"Skipping invalid annotation: surface '{ann.surface}' "
                                f"not found in sentence (year={exam.year}, q={sentence.question})"
                            )
                            continue
                        phrase_key = ann.surface.lower()
                        phrase_map[phrase_key].append(
                            LemmaOccurrence(
                                pos="PHRASE",
                                surface=ann.surface,
                                sentence=sentence.text,
                                role=ann.role,
                                source=sentence_source,
                            )
                        )
                    elif ann.type == "word":
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
                                    role=ann.role,
                                    source=sentence_source,
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

                        lemma = token.lemma_.lower()
                        if role is None:
                            lemma_map[lemma].append(
                                LemmaOccurrence(
                                    pos=token.pos_,
                                    surface=token.text,
                                    sentence=sent_text,
                                    role=None,
                                    source=sentence_source,
                                )
                            )

    return lemma_map, phrase_map, distractor_groups


def _process_translation_items(
    exams: list[StructuredExam],
) -> dict[str, list[LemmaOccurrence]]:
    nlp = get_nlp()
    lemma_map: dict[str, list[LemmaOccurrence]] = defaultdict(list)

    for exam in exams:
        for item in exam.translation_items:
            source_info = SourceInfo(
                year=exam.year,
                exam_type=exam.exam_type,
                section_type=SectionType.TRANSLATION,
                question_number=item.question,
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
                            role=AnnotationRole.TESTED_KEYWORD,
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


def _build_distractor_partner_index(
    distractor_groups: list[DistractorGroup],
) -> dict[str, set[str]]:
    partner_index: dict[str, set[str]] = defaultdict(set)

    for group in distractor_groups:
        correct = group.correct_answer.lower()
        distractors = [d.lower() for d in group.distractors]

        all_words = [correct] + distractors
        for word in all_words:
            for other in all_words:
                if other != word:
                    partner_index[word].add(other)

    return partner_index


def clean_and_classify(
    exams: list[StructuredExam],
    official_wordlist: dict[str, OfficialWordEntry],
) -> CleanedVocabData:
    official_lemmas = _build_official_lemma_set(official_wordlist)

    sentence_lemmas, phrase_lemmas, distractor_groups = _process_sentences(exams)
    translation_lemmas = _process_translation_items(exams)

    distractor_partner_index = _build_distractor_partner_index(distractor_groups)

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

    entries: list[CleanedVocabEntry] = []

    for lemma, occurrences in all_lemmas.items():
        occurrences = _dedupe_occurrences(occurrences)

        official = official_wordlist.get(lemma)
        in_official = _check_in_official(lemma, official_lemmas)
        level = int(official.level) if official and official.level.isdigit() else None

        if occurrences:
            tier = _determine_tier(occurrences, in_official)
            partner_count = len(distractor_partner_index.get(lemma.lower(), set()))
            frequency = _calculate_frequency(occurrences, in_official, level, partner_count)
            pos = sorted({_normalize_pos(o.pos) for o in occurrences})
        else:
            tier = VocabTier.BASIC
            frequency = FrequencyData(
                total_occurrences=0,
                tested_count=0,
                year_spread=0,
                weighted_score=0.0,
            )
            pos = [_normalize_pos(p) for p in official.parts_of_speech] if official else []

        valid_pos = {"NOUN", "VERB", "ADJ", "ADV"}
        pos = [p for p in pos if p in valid_pos]
        if not pos:
            continue

        entries.append(
            CleanedVocabEntry(
                lemma=lemma,
                tier=tier,
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

        tier = _determine_tier(occurrences, False)
        frequency = _calculate_frequency(
            occurrences, in_official=False, level=None, distractor_partner_count=0
        )

        entries.append(
            CleanedVocabEntry(
                lemma=phrase,
                tier=tier,
                level=None,
                in_official_list=False,
                pos=["PHRASE"],
                occurrences=occurrences,
                frequency=frequency,
            )
        )

    entries.sort(key=lambda e: e.frequency.weighted_score, reverse=True)

    return CleanedVocabData(
        entries=entries,
        distractor_groups=distractor_groups,
        essay_topics=essay_topics,
    )

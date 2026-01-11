import logging
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Doc

from ..models import (
    AnnotationRole,
    CleanedPatternEntry,
    CleanedPhraseEntry,
    CleanedVocabData,
    CleanedWordEntry,
    ContextSentence,
    ExamType,
    FrequencyData,
    OfficialWordEntry,
    PatternCategory,
    PatternOccurrence,
    PhraseOccurrence,
    SectionType,
    SentenceRole,
    SourceInfo,
    StructuredExam,
)
from ..utils import load_spacy_trf

logger = logging.getLogger(__name__)

# Batch sizes tuned for MPS (Apple Silicon)
# Larger batches for short texts (words/phrases), smaller for sentences
BATCH_SIZE_SHORT = 256  # For annotation surfaces, keywords, phrases
BATCH_SIZE_LONG = 64    # For full sentences

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

TESTED_ROLES = {
    AnnotationRole.CORRECT_ANSWER,
    AnnotationRole.TESTED_KEYWORD,
    AnnotationRole.DISTRACTOR,
}

ACTIVE_TESTED_ROLES = {
    AnnotationRole.CORRECT_ANSWER,
    AnnotationRole.TESTED_KEYWORD,
}

REFERENCE_EXAM_TYPES = {ExamType.GSAT_REF}


@dataclass
class FrequencyCounter:
    """Collects frequency statistics"""

    years: set[int] = field(default_factory=set)
    by_role: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_section: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    by_exam_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tested_count: int = 0
    active_tested_count: int = 0
    total: int = 0

    def add(
        self, year: int, role: AnnotationRole | None, section: SectionType, exam_type: ExamType
    ):
        self.years.add(year)
        role_str = role.value if role else "none"
        self.by_role[role_str] += 1
        self.by_section[section.value] += 1
        self.by_exam_type[exam_type.value] += 1
        self.total += 1

        if role in TESTED_ROLES:
            self.tested_count += 1
        if role in ACTIVE_TESTED_ROLES:
            self.active_tested_count += 1

    def to_frequency_data(self) -> FrequencyData:
        return FrequencyData(
            total_appearances=self.total,
            tested_count=self.tested_count,
            active_tested_count=self.active_tested_count,
            year_spread=len(self.years),
            years=sorted(self.years),
            by_role=dict(self.by_role),
            by_section=dict(self.by_section),
            by_exam_type=dict(self.by_exam_type),
        )


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


def _normalize_adverb_lemma(lemma: str) -> str:
    """
    Heuristic to recover adjective lemmas from -ly adverbs (e.g., optionally -> optional).
    Only applied when the adverb base is likely to be a real headword.
    """
    if lemma.endswith("ally") and len(lemma) > 4:
        return lemma[:-4] + "al"
    if lemma.endswith("ily") and len(lemma) > 3:
        return lemma[:-3] + "y"
    if lemma.endswith("ly") and len(lemma) > 3:
        return lemma[:-2]
    return lemma


def _is_foreign_word(lemma: str) -> bool:
    """Check if word is likely a foreign loanword (contains non-ASCII characters).

    Examples: zōri, café, naïve, résumé
    """
    return not lemma.isascii()


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = load_spacy_trf(disable=("ner",))
    return _nlp


def normalize_phrase(phrase: str, nlp: Language, phrase_cache: dict[str, Doc] | None = None) -> str:
    if phrase_cache is not None and phrase in phrase_cache:
        doc = phrase_cache[phrase]
    else:
        doc = nlp(phrase)
        if phrase_cache is not None:
            phrase_cache[phrase] = doc

    result = []
    for token in doc:
        if token.pos_ == "AUX":
            continue
        if token.pos_ == "VERB":
            result.append(token.lemma_.lower())
        else:
            result.append(token.text.lower())

    return " ".join(result)


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


def _is_valid_phrase(surface: str) -> bool:
    if '"' in surface or '"' in surface or '"' in surface:
        return False

    if ("'" in surface or "'" in surface or "'" in surface) and not re.match(
        r"^[\w\s]+'[\w\s]+$", surface
    ):
        return False

    if len(surface) > 50:
        return False

    words = surface.split()
    if len(words) < 2 or len(words) > 6:
        return False

    if re.search(r"[A-Z][a-z]+\s+[A-Z]", surface):
        return False

    article_pattern = r"^(a|an|the|this|that|these|those|my|your|his|her|its|our|their)\s"
    if re.match(article_pattern, surface.lower()):
        clean = re.sub(article_pattern, "", surface.lower())
        clean_words = clean.split()
        if len(clean_words) < 2:
            return False
        if re.match(r"^\w+\s+of\s+\w+$", clean):
            return False

    common_compositional = {
        "a lot of",
        "a cup of",
        "a piece of",
        "a kind of",
        "a type of",
        "a sort of",
        "a bit of",
        "a number of",
        "a series of",
        "a variety of",
    }
    return surface.lower() not in common_compositional


def _context_fingerprint(text: str) -> str:
    """Lenient fingerprint for deduping near-identical contexts across exams.

    Normalizes to lowercase alphanumerics with collapsed whitespace so LLM
    paraphrases with minor punctuation differences still align.
    """
    text = text.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized:
        return normalized
    return text.strip()


def _should_keep_context(
    lemma: str,
    text: str,
    exam_type: ExamType,
    year: int,
    seen_map: dict[str, dict[str, tuple[ExamType, int]]],
) -> bool:
    """Decide whether to keep a context to avoid ref/trial echoes.

    Rules:
    - First occurrence always kept.
    - If a ref context repeats a fingerprint already seen, drop it to
      avoid double-counting recycled sentences.
    - If the first sighting was ref and an official exam later reuses the
      same sentence, keep the official one (upgrade the record) while keeping
      the historical signal from the ref occurrence.
    - Repeated official contexts are allowed since they represent true
      multi-year occurrences.
    """
    fp = _context_fingerprint(text)
    if not fp:
        return False

    existing = seen_map[lemma].get(fp)
    if existing is None:
        seen_map[lemma][fp] = (exam_type, year)
        return True

    existing_type, _ = existing

    if exam_type not in REFERENCE_EXAM_TYPES and existing_type in REFERENCE_EXAM_TYPES:
        seen_map[lemma][fp] = (exam_type, year)
        return True

    if exam_type in REFERENCE_EXAM_TYPES and existing_type not in REFERENCE_EXAM_TYPES:
        return False

    if exam_type in REFERENCE_EXAM_TYPES and existing_type in REFERENCE_EXAM_TYPES:
        return False

    return True


def _is_quality_context(text: str, sentence_role: SentenceRole | None = None) -> bool:
    """Check if sentence is suitable for WSD context"""
    # Filter out short fragments (regardless of role)
    # All other sentences (including long options) are valid contexts
    return len(text.split()) >= 5


def _find_surface_spans(doc: Doc, surface: str) -> list:
    """Find spans in a sentence doc that correspond to an annotation surface.

    1) Exact char match (case-insensitive) with alignment expansion
    2) Exact token text/lemma match (single token)
    3) Exact token span text match for multi-word surfaces
    """
    surface_clean = surface.strip()
    if not surface_clean:
        return []

    spans = []

    # Char-level search first to preserve original offsets
    for match in re.finditer(re.escape(surface_clean), doc.text, flags=re.IGNORECASE):
        span = doc.char_span(match.start(), match.end(), alignment_mode="expand")
        if span:
            spans.append(span)

    if spans:
        return spans

    surface_lower = surface_clean.lower()

    # Single-token fallback (text or lemma match)
    for token in doc:
        if token.text.lower() == surface_lower or token.lemma_.lower() == surface_lower:
            return [doc[token.i : token.i + 1]]

    # Multi-token fallback: contiguous token text match
    words = surface_lower.split()
    if len(words) > 1:
        token_count = len(doc)
        for i in range(token_count - len(words) + 1):
            span = doc[i : i + len(words)]
            if span.text.lower() == surface_lower:
                return [span]

    return []


@dataclass
class _SentenceTask:
    """Metadata for a sentence to be processed."""

    exam_year: int
    exam_type: ExamType
    section_type: SectionType
    question: int | None
    sentence_role: SentenceRole | None
    text: str
    annotations: list


def _process_sections(
    exams: list[StructuredExam],
    nlp: Language,
    official_wordlist: dict[str, OfficialWordEntry],
    doc_cache: dict[str, Doc],
    context_seen: dict[str, dict[str, tuple[ExamType, int]]],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[
    dict[str, FrequencyCounter],
    dict[str, list[ContextSentence]],
    dict[str, list[PhraseOccurrence]],
    dict[str, list[PatternOccurrence]],
]:
    frequency_counters: dict[str, FrequencyCounter] = defaultdict(FrequencyCounter)
    contexts_map: dict[str, list[ContextSentence]] = defaultdict(list)
    phrase_map: dict[str, list[PhraseOccurrence]] = defaultdict(list)
    pattern_map: dict[str, list[PatternOccurrence]] = defaultdict(list)

    sentence_tasks: list[_SentenceTask] = []
    phrase_surfaces: list[str] = []

    for exam in exams:
        for section in exam.sections:
            for sentence in section.sentences:
                annotations = sentence.annotations or []

                for ann in annotations:
                    if ann.role == AnnotationRole.NOTABLE_PATTERN:
                        if ann.pattern_category is None:
                            logger.warning(
                                f"Pattern annotation missing category: '{ann.surface}' "
                                f"(year={exam.year}, q={sentence.question})"
                            )
                            continue

                        source = SourceInfo(
                            year=exam.year,
                            exam_type=exam.exam_type,
                            section_type=section.type,
                            question_number=sentence.question,
                            sentence_role=sentence.sentence_role,
                            role=ann.role,
                        )
                        pattern_key = f"{ann.pattern_category.value}"
                        pattern_map[pattern_key].append(
                            PatternOccurrence(
                                pattern_subtype=ann.pattern_subtype,
                                surface=ann.surface,
                                sentence=sentence.text,
                                source=source,
                            )
                        )

                    elif ann.role == AnnotationRole.NOTABLE_PHRASE:
                        if not _is_valid_surface(ann.surface, sentence.text):
                            logger.warning(
                                f"Skipping invalid phrase: surface '{ann.surface}' "
                                f"not found in sentence (year={exam.year}, q={sentence.question})"
                            )
                            continue
                        if not _is_valid_phrase(ann.surface):
                            logger.warning(
                                f"Skipping invalid phrase format: '{ann.surface}' "
                                f"(year={exam.year}, q={sentence.question})"
                            )
                            continue
                        phrase_surfaces.append(ann.surface)

                if sentence.sentence_role != SentenceRole.QUESTION_PROMPT:
                    sentence_tasks.append(
                        _SentenceTask(
                            exam_year=exam.year,
                            exam_type=exam.exam_type,
                            section_type=section.type,
                            question=sentence.question,
                            sentence_role=sentence.sentence_role,
                            text=sentence.text,
                            annotations=annotations,
                        )
                    )

    total_tasks = len(sentence_tasks) + len(phrase_surfaces)
    completed = 0

    unique_phrases = list(set(phrase_surfaces))
    phrases_to_parse = [p for p in unique_phrases if p not in doc_cache]
    if phrases_to_parse:
        for doc, phrase in zip(
            nlp.pipe(phrases_to_parse, batch_size=BATCH_SIZE_SHORT), phrases_to_parse, strict=True
        ):
            doc_cache[phrase] = doc

    phrase_cache: dict[str, Doc] = {}
    for p in unique_phrases:
        if p in doc_cache:
            phrase_cache[p] = doc_cache[p]

    for exam in exams:
        for section in exam.sections:
            for sentence in section.sentences:
                annotations = sentence.annotations or []
                for ann in annotations:
                    if ann.role == AnnotationRole.NOTABLE_PHRASE:
                        if not _is_valid_surface(ann.surface, sentence.text):
                            continue
                        if not _is_valid_phrase(ann.surface):
                            continue

                        normalized = normalize_phrase(ann.surface, nlp, phrase_cache)
                        source = SourceInfo(
                            year=exam.year,
                            exam_type=exam.exam_type,
                            section_type=section.type,
                            question_number=sentence.question,
                            sentence_role=sentence.sentence_role,
                            role=ann.role,
                        )
                        phrase_map[normalized].append(
                            PhraseOccurrence(
                                surface=ann.surface,
                                sentence=sentence.text,
                                source=source,
                            )
                        )

    completed += len(phrase_surfaces)
    if progress_callback:
        progress_callback(completed, total_tasks, "phrases")

    sentence_texts = [t.text for t in sentence_tasks]
    texts_to_parse = [t for t in sentence_texts if t not in doc_cache]
    unique_texts = list(set(texts_to_parse))
    if unique_texts:
        for doc, text in zip(
            nlp.pipe(unique_texts, batch_size=BATCH_SIZE_LONG), unique_texts, strict=True
        ):
            doc_cache[text] = doc

    for i, task in enumerate(sentence_tasks):
        doc = doc_cache[task.text]
        base_source = SourceInfo(
            year=task.exam_year,
            exam_type=task.exam_type,
            section_type=task.section_type,
            question_number=task.question,
            sentence_role=task.sentence_role,
            role=None,
        )

        token_annotations: dict[int, tuple[AnnotationRole, str]] = {}
        unmatched_annotations: list = []
        for ann in task.annotations or []:
            if ann.role not in (
                AnnotationRole.CORRECT_ANSWER,
                AnnotationRole.DISTRACTOR,
                AnnotationRole.TESTED_KEYWORD,
            ):
                continue
            spans = _find_surface_spans(doc, ann.surface)
            if not spans:
                logger.warning(
                    "Annotation surface not aligned to sentence: '%s' (year=%s, q=%s)",
                    ann.surface,
                    task.exam_year,
                    task.question,
                )
                unmatched_annotations.append(ann)
                continue
            for span in spans:
                for token in span:
                    if token.i not in token_annotations:
                        token_annotations[token.i] = (ann.role, ann.surface)
        # Handle annotations that do not appear in the sentence (e.g., vocab options)
        for ann in unmatched_annotations:
            surface_doc = doc_cache.get(ann.surface)
            if surface_doc is None:
                surface_doc = nlp(ann.surface)
                doc_cache[ann.surface] = surface_doc
            for token in surface_doc:
                pos = _normalize_pos(token.pos_)
                if pos in STOP_POS:
                    continue
                if not token.is_alpha or len(token.lemma_) <= 1:
                    continue
                lemma = token.lemma_.lower()
                if _is_foreign_word(lemma):
                    continue
                if pos == "ADV":
                    adv_base = _normalize_adverb_lemma(lemma)
                    if adv_base != lemma and (
                        adv_base in official_wordlist or adv_base in frequency_counters
                    ):
                        lemma = adv_base
                if not _should_keep_context(
                    lemma, task.text, task.exam_type, task.exam_year, context_seen
                ):
                    continue
                frequency_counters[lemma].add(
                    year=task.exam_year,
                    role=ann.role,
                    section=task.section_type,
                    exam_type=task.exam_type,
                )
                if ann.role == AnnotationRole.DISTRACTOR:
                    continue
                if _is_quality_context(task.text, task.sentence_role):
                    contexts_map[lemma].append(
                        ContextSentence(
                            text=task.text,
                            source=base_source.model_copy(update={"role": ann.role}),
                            pos=pos,
                            surface=ann.surface,
                        )
                    )

        for sent in doc.sents:
            sent_text = sent.text.strip()
            for token in sent:
                pos = _normalize_pos(token.pos_)
                if pos in STOP_POS:
                    continue
                if not token.is_alpha:
                    continue
                if token.is_stop:
                    continue
                if len(token.lemma_) <= 1:
                    continue

                role_surface = token_annotations.get(token.i)
                role = role_surface[0] if role_surface else None
                lemma = token.lemma_.lower()
                if _is_foreign_word(lemma):
                    continue
                if pos == "ADV":
                    adv_base = _normalize_adverb_lemma(lemma)
                    if adv_base != lemma and (
                        adv_base in official_wordlist or adv_base in frequency_counters
                    ):
                        lemma = adv_base

                if not _should_keep_context(
                    lemma, sent_text, task.exam_type, task.exam_year, context_seen
                ):
                    continue

                frequency_counters[lemma].add(
                    year=task.exam_year,
                    role=role,
                    section=task.section_type,
                    exam_type=task.exam_type,
                )

                if role == AnnotationRole.DISTRACTOR:
                    continue

                if _is_quality_context(sent_text, task.sentence_role):
                    contexts_map[lemma].append(
                        ContextSentence(
                            text=sent_text,
                            source=base_source.model_copy(update={"role": role}),
                            pos=pos,
                            surface=role_surface[1] if role_surface else token.text,
                        )
                    )

        if progress_callback and (i + 1) % 200 == 0:
            progress_callback(completed + i + 1, total_tasks, "sentences")

    return frequency_counters, contexts_map, phrase_map, pattern_map


def _process_translation_items(
    exams: list[StructuredExam],
    nlp: Language,
    official_wordlist: dict[str, OfficialWordEntry],
    doc_cache: dict[str, Doc],
    context_seen: dict[str, dict[str, tuple[ExamType, int]]],
) -> tuple[dict[str, FrequencyCounter], dict[str, list[ContextSentence]]]:
    frequency_counters: dict[str, FrequencyCounter] = defaultdict(FrequencyCounter)
    contexts_map: dict[str, list[ContextSentence]] = defaultdict(list)

    keywords_to_parse: list[tuple[str, int, ExamType, int | None, str]] = []

    for exam in exams:
        for item in exam.translation_items:
            for keyword in item.keywords:
                keywords_to_parse.append(
                    (keyword, exam.year, exam.exam_type, item.question, item.chinese_prompt)
                )

    unique_keywords = list({k[0] for k in keywords_to_parse})
    to_parse = [k for k in unique_keywords if k not in doc_cache]
    if to_parse:
        for doc, keyword in zip(nlp.pipe(to_parse, batch_size=BATCH_SIZE_SHORT), to_parse, strict=True):
            doc_cache[keyword] = doc

    for keyword, year, exam_type, question, chinese_prompt in keywords_to_parse:
        doc = doc_cache[keyword]
        source_info = SourceInfo(
            year=year,
            exam_type=exam_type,
            section_type=SectionType.TRANSLATION,
            question_number=question,
            role=AnnotationRole.TESTED_KEYWORD,
            sentence_role=None,
        )

        for token in doc:
            pos = _normalize_pos(token.pos_)
            if pos in STOP_POS:
                continue
            if not token.is_alpha or len(token.lemma_) <= 1:
                continue

            lemma = token.lemma_.lower()
            if _is_foreign_word(lemma):
                continue
            if pos == "ADV":
                adv_base = _normalize_adverb_lemma(lemma)
                if adv_base != lemma and (
                    adv_base in official_wordlist or adv_base in frequency_counters
                ):
                    lemma = adv_base

            if not _should_keep_context(lemma, chinese_prompt, exam_type, year, context_seen):
                continue

            frequency_counters[lemma].add(
                year=year,
                role=AnnotationRole.TESTED_KEYWORD,
                section=SectionType.TRANSLATION,
                exam_type=exam_type,
            )

            contexts_map[lemma].append(
                ContextSentence(
                    text=chinese_prompt,
                    source=source_info,
                    pos=pos,
                    surface=keyword,
                )
            )

    return frequency_counters, contexts_map


def _process_essay_suggested_words(
    exams: list[StructuredExam],
    nlp: Language,
    official_wordlist: dict[str, OfficialWordEntry],
    doc_cache: dict[str, Doc],
    context_seen: dict[str, dict[str, tuple[ExamType, int]]],
) -> tuple[dict[str, FrequencyCounter], dict[str, list[ContextSentence]]]:
    frequency_counters: dict[str, FrequencyCounter] = defaultdict(FrequencyCounter)
    contexts_map: dict[str, list[ContextSentence]] = defaultdict(list)

    words_to_parse: list[tuple[str, int, ExamType, str]] = []

    for exam in exams:
        for topic in exam.essay_topics:
            for word in topic.suggested_words:
                words_to_parse.append((word, exam.year, exam.exam_type, topic.description))

    unique_words = list({w[0] for w in words_to_parse})
    to_parse = [w for w in unique_words if w not in doc_cache]
    if to_parse:
        for doc, word in zip(nlp.pipe(to_parse, batch_size=BATCH_SIZE_SHORT), to_parse, strict=True):
            doc_cache[word] = doc

    for word, year, exam_type, description in words_to_parse:
        doc = doc_cache[word]
        source_info = SourceInfo(
            year=year,
            exam_type=exam_type,
            section_type=SectionType.ESSAY,
            question_number=None,
            role=None,
            sentence_role=None,
        )

        for token in doc:
            pos = _normalize_pos(token.pos_)
            if pos in STOP_POS:
                continue
            if not token.is_alpha or len(token.lemma_) <= 1:
                continue

            lemma = token.lemma_.lower()
            if _is_foreign_word(lemma):
                continue
            if pos == "ADV":
                adv_base = _normalize_adverb_lemma(lemma)
                if adv_base != lemma and (
                    adv_base in official_wordlist or adv_base in frequency_counters
                ):
                    lemma = adv_base

            if not _should_keep_context(lemma, description, exam_type, year, context_seen):
                continue

            frequency_counters[lemma].add(
                year=year,
                role=None,
                section=SectionType.ESSAY,
                exam_type=exam_type,
            )

            contexts_map[lemma].append(
                ContextSentence(
                    text=description,
                    source=source_info,
                    pos=pos,
                    surface=word,
                )
            )

    return frequency_counters, contexts_map


def _dedupe_contexts(contexts: list[ContextSentence]) -> list[ContextSentence]:
    seen = set()
    primary_seen_fp: set[str] = set()
    result = []

    def priority(exam_type: ExamType) -> int:
        return 1 if exam_type in REFERENCE_EXAM_TYPES else 0

    for ctx in sorted(contexts, key=lambda c: (priority(c.source.exam_type), c.source.year)):
        if re.search(r"__\d+__", ctx.text):
            continue

        fp = _context_fingerprint(ctx.text)
        if fp and fp in primary_seen_fp and ctx.source.exam_type in REFERENCE_EXAM_TYPES:
            continue

        key = (ctx.text.strip(), ctx.source.year, ctx.source.question_number)
        if key in seen:
            continue

        if fp and ctx.source.exam_type not in REFERENCE_EXAM_TYPES:
            primary_seen_fp.add(fp)

        seen.add(key)
        result.append(ctx)

    return result


def _build_phrase_matcher_patterns(phrase_lemma: str, nlp) -> list[list[dict]]:
    """
    Build spaCy Matcher patterns for a phrase.
    Handles verb conjugation and optional adverb insertion.
    """
    phrase_doc = nlp(phrase_lemma)
    tokens = [t for t in phrase_doc if not t.is_space and not t.is_punct]

    if len(tokens) < 2:
        return []

    first_token = tokens[0]
    rest_tokens = tokens[1:]
    patterns = []

    if first_token.pos_ in ("VERB", "AUX"):
        verb_lemma = first_token.lemma_.lower()
        particles = [t.text.lower() for t in rest_tokens]

        # Pattern 1: Consecutive (e.g., "draw on")
        base = [{"LEMMA": verb_lemma}]
        for p in particles:
            base.append({"LOWER": p})
        patterns.append(base)

        # Pattern 2: Allow one adverb insertion (e.g., "draw heavily on")
        if len(particles) == 1:
            patterns.append(
                [
                    {"LEMMA": verb_lemma},
                    {"POS": "ADV", "OP": "?"},
                    {"LOWER": particles[0]},
                ]
            )

        # Pattern 3: Allow adverb after first particle for 3-word phrases
        if len(particles) == 2:
            patterns.append(
                [
                    {"LEMMA": verb_lemma},
                    {"LOWER": particles[0]},
                    {"POS": "ADV", "OP": "?"},
                    {"LOWER": particles[1]},
                ]
            )
    else:
        # Non-verb phrase (e.g., "in terms of", "as a result")
        pattern = [{"LOWER": t.text.lower()} for t in tokens]
        patterns.append(pattern)

        # Allow determiner variation for phrases starting with article
        if tokens[0].pos_ == "DET" and len(tokens) >= 3:
            pattern_with_any_det = [{"POS": "DET"}]
            for t in tokens[1:]:
                pattern_with_any_det.append({"LOWER": t.text.lower()})
            patterns.append(pattern_with_any_det)

    return patterns


def _backfill_phrase_occurrences(
    exams: list[StructuredExam],
    phrase_map: dict[str, list[PhraseOccurrence]],
    nlp: Language,
    doc_cache: dict[str, Doc],
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, list[PhraseOccurrence]]:
    """
    Scan all sentences to find additional occurrences of known phrases.
    This compensates for LLM annotation inconsistency.
    Reuses doc_cache from previous processing stages.
    """
    if not phrase_map:
        return phrase_map

    known_phrases = list(phrase_map.keys())
    logger.info(f"Backfilling phrases: scanning for {len(known_phrases)} known phrases")

    matcher = Matcher(nlp.vocab)
    phrase_to_rule_ids: dict[str, list[str]] = defaultdict(list)

    for phrase in known_phrases:
        patterns = _build_phrase_matcher_patterns(phrase, nlp)
        for i, pattern in enumerate(patterns):
            rule_id = f"{phrase}__p{i}"
            try:
                matcher.add(rule_id, [pattern])
                phrase_to_rule_ids[phrase].append(rule_id)
            except Exception as e:
                logger.warning(f"Failed to add pattern for '{phrase}': {e}")

    existing_keys: set[tuple[str, str, int, int | None]] = set()
    for phrase, occurrences in phrase_map.items():
        for occ in occurrences:
            key = (phrase, occ.sentence.strip(), occ.source.year, occ.source.question_number)
            existing_keys.add(key)

    rule_to_phrase = {}
    for phrase, rule_ids in phrase_to_rule_ids.items():
        for rule_id in rule_ids:
            rule_to_phrase[rule_id] = phrase

    sentences_to_process: list[
        tuple[str, int, ExamType, SectionType, int | None, SentenceRole | None]
    ] = []
    for exam in exams:
        for section in exam.sections:
            for sentence in section.sentences:
                if not sentence.text or len(sentence.text) < 10:
                    continue
                if sentence.sentence_role == SentenceRole.QUESTION_PROMPT:
                    continue
                sentences_to_process.append(
                    (
                        sentence.text,
                        exam.year,
                        exam.exam_type,
                        section.type,
                        sentence.question,
                        sentence.sentence_role,
                    )
                )

    total_sentences = len(sentences_to_process)
    texts_to_parse = [s[0] for s in sentences_to_process if s[0] not in doc_cache]
    unique_texts = list(set(texts_to_parse))
    if unique_texts:
        for doc, text in zip(
            nlp.pipe(unique_texts, batch_size=BATCH_SIZE_LONG), unique_texts, strict=True
        ):
            doc_cache[text] = doc

    new_occurrences = 0
    for i, (text, year, exam_type, section_type, question, sentence_role) in enumerate(
        sentences_to_process
    ):
        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total_sentences, "backfill")

        doc = doc_cache[text]
        matches = matcher(doc)

        seen_spans = set()
        for match_id, start, end in matches:
            span_key = (start, end)
            if span_key in seen_spans:
                continue
            seen_spans.add(span_key)

            rule_name = nlp.vocab.strings[match_id]
            phrase = rule_to_phrase.get(rule_name)
            if not phrase:
                continue

            surface = doc[start:end].text

            dedup_key = (phrase, text.strip(), year, question)
            if dedup_key in existing_keys:
                continue

            existing_keys.add(dedup_key)

            source = SourceInfo(
                year=year,
                exam_type=exam_type,
                section_type=section_type,
                question_number=question,
                role=AnnotationRole.NOTABLE_PHRASE,
                sentence_role=sentence_role,
            )

            phrase_map[phrase].append(
                PhraseOccurrence(
                    surface=surface,
                    sentence=text,
                    source=source,
                )
            )
            new_occurrences += 1

    logger.info(f"Backfill complete: added {new_occurrences} new phrase occurrences")
    return phrase_map


def _dedupe_phrase_occurrences(occurrences: list[PhraseOccurrence]) -> list[PhraseOccurrence]:
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


# Sections that contain full passages/articles where domain-specific vocabulary appears
PASSAGE_SECTIONS = {
    SectionType.READING,    # Reading Comprehension
    SectionType.MIXED,      # Mixed Questions
    SectionType.CLOZE,      # Cloze Test (綜合測驗)
    SectionType.DISCOURSE,  # Discourse Cloze (文意選填)
}


def _is_passage_specific_single_year(contexts: list[ContextSentence]) -> bool:
    """Check if word only appears in a single passage section in one year.

    Goal: Filter out domain-specific vocabulary that appears in article-based sections
    and is unlikely to be tested again (e.g., "kale", "vodka", "pediatric").

    Filtering criteria (all must be true):
    1. Appears in only one year (excluding gsat_ref to avoid double-counting)
    2. Appears in only one section type
    3. That section type must be a passage section (reading/mixed/cloze/discourse)

    Edge cases preserved:
    - Appears across multiple years → keep (shows recurrence)
    - Appears in multiple sections (e.g., reading + mixed) → keep (used in different contexts)
    - Appears in passage + non-passage (e.g., reading + vocabulary) → keep (likely valuable)
    - Only appears in gsat_ref → filter (no official exam appearance)

    Special handling for gsat_ref:
    - gsat_ref may copy content from official exams, causing false "multi-year" signals
    - We exclude gsat_ref when counting years to avoid this issue
    - If ONLY gsat_ref exists, we still filter it if it meets other criteria
    """
    if not contexts:
        return False

    # Separate gsat_ref from primary exam types to avoid double-counting
    primary_contexts = [c for c in contexts if c.source.exam_type != ExamType.GSAT_REF]

    if not primary_contexts:
        # Only gsat_ref exists - check if single year + single passage section
        years = {c.source.year for c in contexts}
        sections = {c.source.section_type for c in contexts}
        return (
            len(years) == 1
            and len(sections) == 1
            and sections.pop() in PASSAGE_SECTIONS
        )

    # Check primary contexts (non-ref exams)
    primary_years = {c.source.year for c in primary_contexts}
    if len(primary_years) > 1:
        return False  # Multi-year appearance → keep

    primary_sections = {c.source.section_type for c in primary_contexts}

    # If appears in non-passage sections → keep (e.g., vocabulary tests)
    non_passage = primary_sections - PASSAGE_SECTIONS
    if non_passage:
        return False

    # Single year + single passage section → filter (return True)
    # Multiple passage sections → keep (return False)
    return len(primary_sections) == 1


def _is_incidental_vocab(freq_counter: FrequencyCounter) -> bool:
    """Check if word was never tested (only appeared as background context)."""
    return freq_counter.tested_count == 0


def clean_and_aggregate(
    exams: list[StructuredExam],
    official_wordlist: dict[str, OfficialWordEntry],
    exam_only: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> CleanedVocabData:
    nlp = get_nlp()
    doc_cache: dict[str, Doc] = {}
    context_seen: dict[str, dict[str, tuple[ExamType, int]]] = defaultdict(dict)

    if progress_callback:
        progress_callback(0, 100, "processing sections")

    section_freq, section_contexts, phrase_map, pattern_map = _process_sections(
        exams, nlp, official_wordlist, doc_cache, context_seen, progress_callback
    )

    if progress_callback:
        progress_callback(30, 100, "processing translations")

    translation_freq, translation_contexts = _process_translation_items(
        exams, nlp, official_wordlist, doc_cache, context_seen
    )

    if progress_callback:
        progress_callback(40, 100, "processing essays")

    essay_freq, essay_contexts = _process_essay_suggested_words(
        exams, nlp, official_wordlist, doc_cache, context_seen
    )

    if progress_callback:
        progress_callback(50, 100, "backfilling phrases")

    phrase_map = _backfill_phrase_occurrences(exams, phrase_map, nlp, doc_cache, progress_callback)

    logger.info(f"Doc cache size: {len(doc_cache)} unique texts parsed")

    if progress_callback:
        progress_callback(80, 100, "merging data")

    # Merge frequency counters
    all_frequency: dict[str, FrequencyCounter] = defaultdict(FrequencyCounter)
    for lemma, counter in section_freq.items():
        all_frequency[lemma].years.update(counter.years)
        for role, count in counter.by_role.items():
            all_frequency[lemma].by_role[role] += count
        for section, count in counter.by_section.items():
            all_frequency[lemma].by_section[section] += count
        for exam_type, count in counter.by_exam_type.items():
            all_frequency[lemma].by_exam_type[exam_type] += count
        all_frequency[lemma].tested_count += counter.tested_count
        all_frequency[lemma].active_tested_count += counter.active_tested_count
        all_frequency[lemma].total += counter.total

    for lemma, counter in translation_freq.items():
        all_frequency[lemma].years.update(counter.years)
        for role, count in counter.by_role.items():
            all_frequency[lemma].by_role[role] += count
        for section, count in counter.by_section.items():
            all_frequency[lemma].by_section[section] += count
        for exam_type, count in counter.by_exam_type.items():
            all_frequency[lemma].by_exam_type[exam_type] += count
        all_frequency[lemma].tested_count += counter.tested_count
        all_frequency[lemma].active_tested_count += counter.active_tested_count
        all_frequency[lemma].total += counter.total

    for lemma, counter in essay_freq.items():
        all_frequency[lemma].years.update(counter.years)
        for role, count in counter.by_role.items():
            all_frequency[lemma].by_role[role] += count
        for section, count in counter.by_section.items():
            all_frequency[lemma].by_section[section] += count
        for exam_type, count in counter.by_exam_type.items():
            all_frequency[lemma].by_exam_type[exam_type] += count
        all_frequency[lemma].tested_count += counter.tested_count
        all_frequency[lemma].active_tested_count += counter.active_tested_count
        all_frequency[lemma].total += counter.total

    # Merge contexts
    all_contexts: dict[str, list[ContextSentence]] = defaultdict(list)
    for lemma, contexts in section_contexts.items():
        all_contexts[lemma].extend(contexts)
    for lemma, contexts in translation_contexts.items():
        all_contexts[lemma].extend(contexts)
    for lemma, contexts in essay_contexts.items():
        all_contexts[lemma].extend(contexts)

    # Add official wordlist if needed
    if not exam_only:
        for word in official_wordlist:
            if word not in all_frequency:
                all_frequency[word] = FrequencyCounter()

    words: list[CleanedWordEntry] = []
    phrases: list[CleanedPhraseEntry] = []
    patterns: list[CleanedPatternEntry] = []
    filtered_passage_specific = 0

    # Build word entries
    for lemma, freq_counter in all_frequency.items():
        contexts = _dedupe_contexts(all_contexts.get(lemma, []))

        official = official_wordlist.get(lemma)
        in_official = official is not None
        level = int(official.level) if official and official.level.isdigit() else None

        # Filter out rare passage-specific vocabulary:
        # - Not in official wordlist
        # - Never tested (only background context)
        # - Single year + single passage section (reading/mixed/cloze/discourse)
        if (
            not in_official
            and _is_incidental_vocab(freq_counter)
            and _is_passage_specific_single_year(contexts)
        ):
            filtered_passage_specific += 1
            continue

        if contexts:
            pos = sorted({ctx.pos for ctx in contexts})
        else:
            pos = [_normalize_pos(p) for p in official.parts_of_speech] if official else []

        valid_pos = {"NOUN", "VERB", "ADJ", "ADV"}
        pos = [p for p in pos if p in valid_pos]
        if not pos:
            continue

        words.append(
            CleanedWordEntry(
                lemma=lemma,
                level=level,
                in_official_list=in_official,
                pos=pos,
                frequency=freq_counter.to_frequency_data(),
                contexts=contexts,
            )
        )

    # Build phrase entries
    for phrase, occurrences in phrase_map.items():
        occurrences = _dedupe_phrase_occurrences(occurrences)
        if not occurrences:
            continue

        # Build frequency from occurrences
        freq_counter = FrequencyCounter()
        contexts = []
        for occ in occurrences:
            freq_counter.add(
                year=occ.source.year,
                role=occ.source.role,
                section=occ.source.section_type,
                exam_type=occ.source.exam_type,
            )
            if _is_quality_context(occ.sentence, occ.source.sentence_role):
                contexts.append(
                    ContextSentence(
                        text=occ.sentence,
                        source=occ.source,
                        pos="",
                        surface=occ.surface,
                    )
                )

        phrases.append(
            CleanedPhraseEntry(
                lemma=phrase,
                frequency=freq_counter.to_frequency_data(),
                contexts=contexts,
            )
        )

    # Build pattern entries
    for category_key, occurrences in pattern_map.items():
        occurrences = _dedupe_pattern_occurrences(occurrences)
        if not occurrences:
            continue

        pattern_category = PatternCategory(category_key)

        patterns.append(
            CleanedPatternEntry(
                pattern_category=pattern_category,
                occurrences=occurrences,
            )
        )

    if filtered_passage_specific > 0:
        logger.info(f"Filtered {filtered_passage_specific} passage-specific incidental words")

    return CleanedVocabData(
        words=words,
        phrases=phrases,
        patterns=patterns,
    )


def clean_and_classify(
    exams: list[StructuredExam],
    official_wordlist: dict[str, OfficialWordEntry],
    exam_only: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> CleanedVocabData:
    return clean_and_aggregate(exams, official_wordlist, exam_only, progress_callback)

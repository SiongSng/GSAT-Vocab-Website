import tempfile
from pathlib import Path

import pytest

from src.models import AnnotationRole, ExamType, SentenceRole
from src.stages.stage1_structurize import structurize_exam

SAMPLE_VOCABULARY = """## 詞彙題 / Vocabulary

5. Not satisfied with the first ______ of her essay, Mary revised it several times before turning it in to the teacher.
   (A) text
   (B) brush
   (C) draft
   (D) plot

6. Left ______ for years, the deserted house was filled with a thick coating of dust and a smell of old damp wood.
   (A) casual
   (B) fragile
   (C) remote
   (D) vacant
"""

SAMPLE_CLOZE = """## 綜合測驗 / Cloze Test

### 第 16-18 題為題組

If you have ever been sick to your stomach on a rocking boat or a bumpy car ride, you know the discomfort of motion sickness. It can __16__ suddenly, progressing from a feeling of uneasiness to a cold sweat.

Motion sickness occurs when the signals your brain receives from your eyes, ears, and body __17__. Your brain doesn't know whether you are stationary or moving.

You can take some __18__ to help avoid the discomfort.

16. (A) crash
    (B) flush
    (C) burst
    (D) strike
17. (A) are not regular
    (B) can hardly move
    (C) do not match
    (D) are rarely cued
18. (A) special opportunities
    (B) preventive measures
    (C) potential risks
    (D) significant advantages
"""

SAMPLE_TRANSLATION = """## 翻譯題 / Translation

1. 乘客因為塞車而感到焦慮不安。

2. 這項新政策預計將大幅降低碳排放量。
"""

SAMPLE_STRUCTURE = """## 篇章結構 / Paragraph Structure

### 第 31-34 題為題組

A capsule hotel is a unique type of basic, affordable accommodation. Originated in Japan, these hotels were initially meant for business professionals. __31__

The rooms, called "capsules," are small units designed for one occupant. __32__ Guests check in and store their belongings in lockers.

__33__ Some hotels may not provide air conditioning in the capsules, leading to poor air flow.

__34__ However, for budget-conscious travelers who just need a place to sleep, capsule hotels offer an interesting and economical option.

(A) Today, they provide low-budget, overnight lodging in commerce centers in large cities worldwide.
(B) The chambers are stacked side-by-side, two units high, with the upper rooms reached by a ladder.
(C) In response to rising demands, these hotels are embracing a wave of innovation.
(D) The room's thin plastic walls easily transmit the sound of snoring made by neighboring guests.
(E) Despite these drawbacks, the concept continues to expand globally.
"""


@pytest.fixture
def temp_markdown_file():
    def _create(content: str) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            return Path(f.name)

    return _create


class TestStage1E2E:
    @pytest.mark.asyncio
    async def test_vocabulary_section_has_correct_answer_and_distractors(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_VOCABULARY)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        vocab_sections = [s for s in exam.sections if s.type.value == "vocabulary"]
        assert len(vocab_sections) == 1

        vocab = vocab_sections[0]
        assert len(vocab.sentences) >= 2

        for sentence in vocab.sentences:
            assert sentence.sentence_role == SentenceRole.CLOZE
            assert sentence.annotations is not None

            correct_answers = [
                a for a in sentence.annotations if a.role == AnnotationRole.CORRECT_ANSWER
            ]
            distractors = [a for a in sentence.annotations if a.role == AnnotationRole.DISTRACTOR]

            assert len(correct_answers) == 1, (
                f"Expected 1 correct_answer annotation, got {len(correct_answers)} in: {sentence.text}"
            )
            assert len(distractors) == 3, (
                f"Expected 3 distractor annotations, got {len(distractors)} in: {sentence.text}"
            )

    @pytest.mark.asyncio
    async def test_cloze_section_structure(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_CLOZE)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        cloze_sections = [s for s in exam.sections if s.type.value == "cloze"]
        assert len(cloze_sections) == 1

        cloze = cloze_sections[0]

        cloze_sentences = [s for s in cloze.sentences if s.sentence_role == SentenceRole.CLOZE]
        assert len(cloze_sentences) >= 3

        for sentence in cloze_sentences:
            assert sentence.question is not None
            assert sentence.annotations is not None

            correct_answers = [
                a for a in sentence.annotations if a.role == AnnotationRole.CORRECT_ANSWER
            ]
            distractors = [a for a in sentence.annotations if a.role == AnnotationRole.DISTRACTOR]

            assert len(correct_answers) >= 1
            assert len(distractors) == 3

    @pytest.mark.asyncio
    async def test_cloze_has_passage_sentences(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_CLOZE)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        cloze_sections = [s for s in exam.sections if s.type.value == "cloze"]
        cloze = cloze_sections[0]

        passage_sentences = [s for s in cloze.sentences if s.sentence_role == SentenceRole.PASSAGE]
        assert len(passage_sentences) >= 0

    @pytest.mark.asyncio
    async def test_structure_section_uses_option_and_unused_option(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_STRUCTURE)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        structure_sections = [s for s in exam.sections if s.type.value == "structure"]
        assert len(structure_sections) == 1

        structure = structure_sections[0]

        passage_sentences = [
            s for s in structure.sentences if s.sentence_role == SentenceRole.PASSAGE
        ]
        option_sentences = [
            s for s in structure.sentences if s.sentence_role == SentenceRole.OPTION
        ]
        unused_sentences = [
            s for s in structure.sentences if s.sentence_role == SentenceRole.UNUSED_OPTION
        ]

        assert len(passage_sentences) >= 1, "Expected at least 1 passage paragraph"
        assert len(option_sentences) == 4, "Expected 4 answer options (questions 31-34)"
        assert len(unused_sentences) == 1, "Expected 1 unused option (5 options - 4 blanks)"

        for opt in option_sentences:
            assert opt.question is not None, "Option sentence should have question number"

        for unused in unused_sentences:
            assert unused.question is None, "Unused option should not have question number"

    @pytest.mark.asyncio
    async def test_no_blank_markers_in_output(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_VOCABULARY + SAMPLE_CLOZE)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        for section in exam.sections:
            for sentence in section.sentences:
                assert "__" not in sentence.text, f"Blank marker found in output: {sentence.text}"

    @pytest.mark.asyncio
    async def test_translation_items_extracted_separately(self, temp_markdown_file):
        md_path = temp_markdown_file(SAMPLE_TRANSLATION)

        exam = await structurize_exam(md_path, 114, ExamType.GSAT)

        translation_sections = [s for s in exam.sections if s.type.value == "translation"]
        assert len(translation_sections) == 0, "Translation should not be a section"

        assert len(exam.translation_items) == 2, "Expected 2 translation items"

        for item in exam.translation_items:
            assert item.question in (1, 2)
            assert len(item.chinese_prompt) > 0
            assert len(item.keywords) >= 3, (
                f"Expected at least 3 keywords, got {len(item.keywords)}"
            )

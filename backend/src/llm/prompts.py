STAGE0_SYSTEM = """You are a document formatter converting Taiwan GSAT/AST English exam PDFs into structured Markdown.

<context>
Your output feeds an NLP pipeline that extracts vocabulary from exam sentences. Accurate structure preservation directly impacts vocabulary analysis quality. The pipeline relies on:
- Question numbers to track which words were tested
- Section headers to classify question types
- Blank markers to identify fill-in-the-blank answers
- Option formatting to extract answer choices
- Question prompts to understand what is being asked
</context>

<formatting_rules>
1. Section headers: Use ## with bilingual labels
   - ## 詞彙題 / Vocabulary
   - ## 綜合測驗 / Cloze Test
   - ## 文意選填 / Discourse Cloze
   - ## 篇章結構 / Paragraph Structure
   - ## 閱讀測驗 / Reading Comprehension
   - ## 翻譯題 / Translation
   - ## 作文題 / Writing
   - ## 混合題 / Mixed Questions

2. Question numbers: Preserve exactly as they appear in the source

3. Blanks: Mark as __N__ where N is the question number
   Example: The __5__ was too heavy to carry.

4. Options: Format as (A) option (B) option (C) option (D) option on the same line

5. Paragraphs: Preserve original paragraph breaks

6. Tables: Convert to Markdown tables

7. Special characters: Preserve all punctuation and special characters

8. Keep blanks empty: Do not fill in answers

9. Question Groups: Format markers indicating a group of questions (e.g. '第 41 至 44 題為題組') as a Level 3 header: `### 第 41-44 題為題組`. Ensure it is on its own line.

10. Question prompts: PRESERVE all instruction text that tells students what to do
    - "請依據文意，填入最適當的答案" → keep this
    - "請根據上文，從 (A) 到 (F) 選出正確答案" → keep this
    - Any text explaining how to answer the question → keep this
</formatting_rules>

<output_format>
Clean Markdown with consistent structure. Each section clearly delimited.
</output_format>
"""

# =============================================================================
# STAGE 1: Markdown → Structured JSON
# =============================================================================

STAGE1_SYSTEM = """You structure Taiwan GSAT English exams into JSON for a vocabulary learning system.

<purpose>
This system helps Taiwanese high school students prepare for GSAT by:
1. Creating flashcards from real exam sentences
2. Highlighting phrasal verbs worth memorizing
3. Identifying grammar patterns teachers emphasize for GSAT
</purpose>

<your_role>
You are an experienced English teacher who knows exactly what Taiwanese high school students need to study. Apply pedagogical judgment — annotate only what genuinely helps students, not everything technically possible.
</your_role>
"""

STAGE1_RULES = """<task>
Convert exam Markdown to structured JSON. Fill in all blanks with correct answers.
</task>

<critical_constraints>
1. Every __N__ blank becomes a cloze sentence with question=N
2. Annotation surface must be an EXACT substring of the sentence (case-sensitive)
3. Output text contains filled answers, never __N__ markers
4. Use ONLY schema-defined values for enums — invent nothing
5. Single-word fields (translation.keywords, essay.suggested_words): Output individual words only, never multi-word phrases. A word contains no spaces. Split phrases into components: "according to" → ["according"], "traffic accidents" → ["traffic", "accidents"]. Phrases are intuitive to students; isolated vocabulary words are what they need to study.
</critical_constraints>

<sentence_roles>
Use these roles to classify each sentence:
- cloze: Originally had a blank, now filled in
- passage: Context paragraph without blanks
- question_prompt: Question text like "What is the main idea?"
- option: Answer choice for reading/structure questions
- unused_option: Unused options in 5-choose-4 or word bank leftovers
</sentence_roles>

<annotations>

## correct_answer / distractor
- correct_answer: The word/phrase filling the blank
- distractor: Wrong options from exam choices
- For vocabulary/cloze sections: exactly 1 correct_answer + 3 distractors

## notable_phrase
Purpose: Mark multi-word expressions that students must memorize because the meaning is NOT deducible from components.

The test: Can a student who knows each word separately guess the phrase's meaning? No → mark it.

Include these types:
1. Phrasal verbs: "give up" → 放棄, "take on" → 承擔
2. Idioms: "a piece of cake" → 很簡單, "break the ice" → 打破僵局
3. Idiomatic phrases: "by and large" → 大致上, "once in a blue moon" → 千載難逢
4. Fixed collocations (opaque): "catch a cold" → 感冒 (why catch?)

Mark when meaning is opaque:
  ✓ "give up" → 放棄 (not deducible from give + up)
  ✓ "take on" → 承擔 (not deducible from take + on)
  ✓ "a piece of cake" → 很簡單 (idiom, not about cake)
  ✓ "break the ice" → 打破僵局 (idiom, not about ice)
  ✓ "by and large" → 大致上 (fixed phrase)
  ✓ "make one's way" → 前進 (not deducible from make + way)
  ✓ "catch a cold" → 感冒 (why "catch"? opaque collocation)

Skip when meaning is transparent:
  ✗ "look at" → 看 (obviously look + at)
  ✗ "go to" → 去 (obviously go + to)
  ✗ "make a decision" → 做決定 (transparent collocation)
  ✗ "grow up" → 長大 (transparent: grow upward → mature)

Surface form: Always use dictionary lemma
  - Sentence has "gave up" → surface is "give up"
  - Sentence has "made its way" → surface is "make one's way"
  - Sentence has "breaking the ice" → surface is "break the ice"

## notable_pattern
Purpose: Mark grammar patterns that GSAT tests and teachers explicitly teach. These appear as dedicated chapters in grammar books.

Verify structure exists — keywords alone are insufficient:
  - Inversion requires auxiliary BEFORE subject
    ✓ "Not only does he sing..." (does before he = inversion)
    ✗ "He is not only smart but also kind" (no inversion, just conjunction)
  - Participle clause must modify the main clause
  - Subjunctive needs mood markers (were, should, past for unreal)

Use schema values only. If no subtype fits, skip the annotation entirely.

</annotations>

<section_processing>

vocabulary:
- All sentences are cloze with question number
- Each: 1 correct_answer + 3 distractors
- Check for notable_phrase/notable_pattern

cloze:
- Blanked sentences → cloze with correct_answer + 3 distractors
- Context paragraphs → passage
- Check notable_phrase/notable_pattern in both

discourse:
- Blanked sentences → cloze with correct_answer
- Context paragraphs → passage
- Unused word bank → unused_option (one per word)

structure:
- Original paragraphs → passage
- Inserted sentences → option with question=N
- Unused sentences → unused_option

reading:
- Article → passage (check notable_phrase/notable_pattern)
- Question text → question_prompt with question=N
- Choices → option with question=N

mixed (post-2022 format):
- fill_in_word: Student extracts word from passage, applies morphology. Use acceptable_answers for alternatives.
- short_answer: Answer is single word/phrase. Text field contains only the answer.
- multiple_select: Standard options with question=N
- Omit Chinese prompts; keep English prompts as question_prompt

translation:
- Use translation_items array (not a section)
- Fields: question, chinese_prompt, keywords
- keywords: 3-6 vocabulary words for the translation (single-word constraint #5 applies)

essay:
- Use essay_topics array
- Fields: description (from 提示), suggested_words
- suggested_words: 5-12 sophisticated vocabulary words (single-word constraint #5 applies)

</section_processing>

<multi_blank_sentences>
When one sentence has multiple blanks (__17__ ... __18__):
- Create separate entries sharing the same filled text
- Each entry has its own question number and annotations
</multi_blank_sentences>

<final_validation>
Before output:
□ Every __N__ has corresponding cloze with question=N
□ Every surface is verbatim substring of sentence
□ Vocabulary/cloze have exactly 1 correct + 3 distractors
□ No __N__ markers remain in text
□ All enum values exist in schema
</final_validation>
"""

STAGE1_EXAMPLES = {
    "vocabulary": """{
  "sections": [{
    "type": "vocabulary",
    "sentences": [
      {
        "text": "Not satisfied with the first draft of her essay, Mary revised it several times before turning it in to the teacher.",
        "sentence_role": "cloze",
        "question": 5,
        "annotations": [
          {"surface": "draft", "role": "correct_answer"},
          {"surface": "text", "role": "distractor"},
          {"surface": "brush", "role": "distractor"},
          {"surface": "plot", "role": "distractor"},
          {"surface": "Not satisfied with", "role": "notable_pattern", "pattern_category": "participle", "pattern_subtype": "perfect_participle"},
          {"surface": "turn in", "role": "notable_phrase"}
        ]
      }
    ]
  }]
}

Why "turn in" is marked: 繳交 cannot be guessed from turn + in.
Why "Not satisfied with" is marked: Participle clause at sentence start — classic GSAT grammar point.""",
    "cloze": """{
  "sections": [{
    "type": "cloze",
    "sentences": [
      {
        "text": "But some mountain ranges are also home to glaciers and ice sheets.",
        "sentence_role": "cloze",
        "question": 11,
        "annotations": [
          {"surface": "home to", "role": "correct_answer"},
          {"surface": "covers of", "role": "distractor"},
          {"surface": "roofs over", "role": "distractor"},
          {"surface": "room for", "role": "distractor"},
          {"surface": "home to", "role": "notable_phrase"}
        ]
      },
      {
        "text": "Having already shrunk by 85%, the glaciers will completely disappear within a decade.",
        "sentence_role": "cloze",
        "question": 13,
        "annotations": [
          {"surface": "Having", "role": "correct_answer"},
          {"surface": "Have", "role": "distractor"},
          {"surface": "Had", "role": "distractor"},
          {"surface": "Having been", "role": "distractor"},
          {"surface": "Having already shrunk by 85%", "role": "notable_pattern", "pattern_category": "participle", "pattern_subtype": "perfect_participle"}
        ]
      },
      {
        "text": "Had it not been for modern medicine, travelers would still suffer greatly.",
        "sentence_role": "cloze",
        "question": 17,
        "annotations": [
          {"surface": "suffer", "role": "correct_answer"},
          {"surface": "differ", "role": "distractor"},
          {"surface": "wander", "role": "distractor"},
          {"surface": "linger", "role": "distractor"},
          {"surface": "Had it not been for", "role": "notable_pattern", "pattern_category": "inversion", "pattern_subtype": "conditional_inversion"}
        ]
      }
    ]
  }]
}

Why "home to" is notable_phrase: "be home to" = 是...的棲息地, not guessable from home + to.
Why "Had it not been for" is inversion: Auxiliary "Had" precedes subject "it" — conditional inversion.""",
    "discourse": """{
  "sections": [{
    "type": "discourse",
    "sentences": [
      {
        "text": "Many people come from far away to pour out their feelings.",
        "sentence_role": "passage",
        "annotations": [
          {"surface": "pour out", "role": "notable_phrase"}
        ]
      },
      {
        "text": "These people often tried out things for the first time during shooting.",
        "sentence_role": "cloze",
        "question": 24,
        "annotations": [
          {"surface": "tried out", "role": "correct_answer"},
          {"surface": "try out", "role": "notable_phrase"}
        ]
      },
      {
        "text": "activated",
        "sentence_role": "unused_option"
      }
    ]
  }]
}

Surface form: correct_answer keeps sentence form "tried out", but notable_phrase uses lemma "try out".""",
    "structure": """{
  "sections": [{
    "type": "structure",
    "sentences": [
      {
        "text": "Having originated in Japan, these hotels were initially meant for business professionals.",
        "sentence_role": "passage",
        "annotations": [
          {"surface": "Having originated in Japan", "role": "notable_pattern", "pattern_category": "participle", "pattern_subtype": "perfect_participle"}
        ]
      },
      {
        "text": "Today, they provide low-budget, overnight lodging in commerce centers.",
        "sentence_role": "option",
        "question": 31
      },
      {
        "text": "The chambers are stacked side-by-side, with the upper rooms reached by a ladder.",
        "sentence_role": "option",
        "question": 32,
        "annotations": [
          {"surface": "with the upper rooms reached by a ladder", "role": "notable_pattern", "pattern_category": "participle", "pattern_subtype": "with_participle"}
        ]
      },
      {
        "text": "However, the small space can feel claustrophobic for some travelers.",
        "sentence_role": "unused_option"
      }
    ]
  }]
}""",
    "reading": """{
  "sections": [{
    "type": "reading",
    "sentences": [
      {
        "text": "They are brave enough to help in an emergency while others may stand by.",
        "sentence_role": "passage",
        "annotations": [
          {"surface": "stand by", "role": "notable_phrase"}
        ]
      },
      {
        "text": "In 1945, devastated from the war, the country set about establishing a cheap industry.",
        "sentence_role": "passage",
        "annotations": [
          {"surface": "set about", "role": "notable_phrase"}
        ]
      },
      {
        "text": "What is the main idea of the passage?",
        "sentence_role": "question_prompt",
        "question": 35
      },
      {
        "text": "The sandals American soldiers brought home later became modern flip-flops.",
        "sentence_role": "option",
        "question": 37
      }
    ]
  }]
}

Why "stand by" and "set about": Meanings (袖手旁觀, 著手) not deducible from components.""",
    "mixed": """{
  "sections": [{
    "type": "mixed",
    "sentences": [
      {
        "text": "From Turkey, she boarded a small boat and set sail into the deep waters.",
        "sentence_role": "passage",
        "annotations": [
          {"surface": "set sail", "role": "notable_phrase"}
        ]
      },
      {
        "text": "Modern zoos serve the purposes of conserving endangered species as well as educating visitors.",
        "sentence_role": "cloze",
        "question": 47,
        "mixed_question_type": "fill_in_word",
        "annotations": [
          {"surface": "educating", "role": "correct_answer"}
        ],
        "acceptable_answers": ["educating", "entertaining"]
      },
      {
        "text": "asylum",
        "sentence_role": "cloze",
        "question": 48,
        "mixed_question_type": "short_answer"
      },
      {
        "text": "Joining the Olympic Games more than once.",
        "sentence_role": "option",
        "question": 49
      }
    ]
  }]
}""",
    "translation": """{
  "translation_items": [
    {
      "question": 1,
      "chinese_prompt": "根據新聞報導，每年全球有超過百萬人在道路事故中喪失性命。",
      "keywords": ["according", "reports", "million", "accidents", "lives"]
    }
  ]
}""",
    "essay": """{
  "essay_topics": [{
    "description": "提示：不同的公園，可能樣貌不同，特色也不同。請以此為主題，寫一篇英文作文。第一段描述兩張圖片中的公園各有何特色，第二段說明你心目中理想公園的樣貌。",
    "suggested_words": ["biodiversity", "tranquility", "sustainability", "amenities", "conservation", "landscaping", "serene"]
  }]
}""",
}

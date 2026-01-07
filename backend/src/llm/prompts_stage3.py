STAGE3_DICT_FILTER_SYSTEM = """You are a bilingual lexicographer specializing in Taiwan's GSAT English education (108 curriculum, CEFR A2-B2). Create concise, student-relevant vocabulary content with clearly distinguishable sense definitions."""

STAGE3_DICT_FILTER_BATCH_PROMPT = """Process dictionary entries into high-quality meaning clusters (1-4 per lemma) for Taiwanese GSAT students.

<output_ordering>
Return clusters ordered by usage frequency for high school students:
1. First cluster = most common everyday meaning (news, textbooks, daily life)
2. Subsequent clusters = progressively less common meanings
3. Last cluster = least frequent among retained senses

This ordering directly affects flashcard presentation. Students see the first cluster by default, so place the most practical, high-frequency meaning first.
</output_ordering>

<sense_selection>
Retain senses that appear in:
- News articles and current events coverage
- Academic and scientific texts (popular science level)
- Official GSAT/CEEC exam materials
- Everyday conversation and practical situations

Include common high-frequency senses from dictionary data even if not in the provided contexts. Students need exposure to all typical usages at GSAT level, not just past exam occurrences.

Merge senses that share the same Chinese translation concept (think: would these map to the same 繁中定義?):
- "available online" + "connected to Internet" → ONE cluster (both = 網路上的)
- "coins for buying" + "wealth in general" → ONE cluster (both = 金錢)

Keep senses separate when Chinese translations differ:
- "deliver package" vs "deliver speech" → SEPARATE clusters (遞送 vs 發表)

Exclude archaic, highly technical, or slang senses outside CEFR A2-B2 scope.
</sense_selection>

<pos_preservation>
Preserve at least one cluster per part of speech when the word commonly functions as multiple POS. A word appearing as both NOUN and VERB in contexts requires clusters for both.
</pos_preservation>

<definition_format>
Format core_meaning as: "繁中定義 (English with distinctive keywords)"
- Use different English vocabulary for each sense to distinguish them
- Include typical collocations: "commit a crime" vs "commit to a goal"
- Add context markers when helpful: "island (land in water)" vs "island (traffic island)"
</definition_format>

<example>
Input:
<lemma name="cook">
  <contexts>She learned cooking from her grandmother.</contexts>
  <senses>
    <sense id="s0" pos="NOUN">a person who prepares food</sense>
    <sense id="s1" pos="VERB">to prepare food by heating</sense>
  </senses>
</lemma>
<lemma name="commit">
  <contexts>He committed a serious crime.</contexts>
  <senses>
    <sense id="s0" pos="VERB">to do something illegal</sense>
    <sense id="s1" pos="VERB">to promise or dedicate</sense>
  </senses>
</lemma>

Output (note: VERB "cook" is more common than NOUN, so it comes first):
{{
  "items": [
    {{
      "lemma": "cook",
      "clusters": [
        {{
          "primary_id": "s1",
          "merged_ids": ["s1"],
          "pos": "VERB",
          "core_meaning": "烹飪 (to prepare food by heating)"
        }},
        {{
          "primary_id": "s0",
          "merged_ids": ["s0"],
          "pos": "NOUN",
          "core_meaning": "廚師 (a person who prepares food professionally)"
        }}
      ]
    }},
    {{
      "lemma": "commit",
      "clusters": [
        {{
          "primary_id": "s0",
          "merged_ids": ["s0"],
          "pos": "VERB",
          "core_meaning": "犯（罪）(to do something illegal, e.g. commit a crime)"
        }},
        {{
          "primary_id": "s1",
          "merged_ids": ["s1"],
          "pos": "VERB",
          "core_meaning": "承諾、投入 (to promise or dedicate, e.g. commit to a goal)"
        }}
      ]
    }}
  ]
}}
</example>

<input>
{lemmas_xml}
</input>

Return JSON only."""

STAGE3_LLMS_DEFINE_SYSTEM = """You are a bilingual lexicographer specializing in Taiwan's GSAT English education (108 curriculum, CEFR A2-B2). Create concise, student-relevant vocabulary content with clearly distinguishable sense definitions."""

STAGE3_LLMS_DEFINE_PROMPT = """Define the word "{lemma}" with 1-4 meaning clusters for GSAT students.

<output_ordering>
Return clusters ordered by usage frequency for high school students:
1. First cluster = most common everyday meaning (news, textbooks, daily life)
2. Subsequent clusters = progressively less common meanings
3. Last cluster = least frequent among retained senses

This ordering directly affects flashcard presentation. Students see the first cluster by default, so place the most practical, high-frequency meaning first.
</output_ordering>

<sense_selection>
Retain senses appearing in: news articles, academic texts (popular science level), GSAT/CEEC materials, everyday conversation.

Include common high-frequency senses even if not in the provided contexts. Students need all typical usages at GSAT level, not just past exam occurrences.

Merge senses sharing the same Chinese translation concept (think: would these map to the same 繁中定義?). Keep separate when Chinese translations clearly differ.

Exclude archaic, highly technical, or slang senses outside CEFR A2-B2 scope.
</sense_selection>

<pos_preservation>
Preserve at least one cluster per part of speech when the word commonly functions as multiple POS.
</pos_preservation>

<definition_format>
Format core_meaning as: "繁中定義 (English with distinctive keywords)"
- Use different English vocabulary for each sense
- Include collocations: "commit a crime" vs "commit to a goal"
</definition_format>

<input>
POS hint: {pos}
Exam contexts:
{contexts_xml}
</input>

<example>
Word: "deliver"
Output (most common meaning first):
{{
  "clusters": [
    {{
      "pos": "VERB",
      "core_meaning": "遞送 (to transport goods or packages to a destination)",
      "examples": ["The courier delivered the package on time."]
    }},
    {{
      "pos": "VERB",
      "core_meaning": "發表 (to give a speech or presentation)",
      "examples": ["She delivered an inspiring speech at the conference."]
    }}
  ]
}}
</example>

Return JSON only."""

STAGE3_LLMS_DEFINE_PHRASE_PROMPT = """Define the phrase "{lemma}" with 1-4 meaning clusters for GSAT students.

<output_ordering>
Return clusters ordered by usage frequency for high school students:
1. First cluster = most common everyday meaning (news, textbooks, daily life)
2. Subsequent clusters = progressively less common meanings
3. Last cluster = least frequent among retained senses

This ordering directly affects flashcard presentation. Students see the first cluster by default, so place the most practical, high-frequency meaning first.
</output_ordering>

<sense_selection>
Retain senses appearing in: news articles, academic texts (popular science level), GSAT/CEEC materials, everyday conversation.

Include common high-frequency senses even if not in the provided contexts. Students need all typical usages at GSAT level, not just past exam occurrences.

Merge senses sharing the same Chinese translation concept (think: would these map to the same 繁中定義?). Keep separate when Chinese translations clearly differ.

Exclude archaic, highly technical, or slang senses outside CEFR A2-B2 scope.
</sense_selection>

<definition_format>
Format core_meaning as: "繁中定義 (English with distinctive keywords)"
- Use different English vocabulary for each sense
- Include usage context and examples when helpful
</definition_format>

<input>
Exam contexts:
{contexts_xml}
</input>

<example>
Phrase: "set up"
Output (most common meaning first):
{{
  "clusters": [
    {{
      "core_meaning": "建立、設置 (to establish or arrange something)",
      "examples": ["We need to set up a meeting with the client."]
    }},
    {{
      "core_meaning": "組裝、安裝 (to assemble or install equipment)",
      "examples": ["It took me an hour to set up the new computer."]
    }}
  ]
}}
</example>

Return JSON only (phrases have no "pos" field)."""

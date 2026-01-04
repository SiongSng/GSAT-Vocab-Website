STAGE3_DICT_FILTER_SYSTEM = """You are a bilingual lexicographer specializing in high school English education (GSAT/CEFR A1-B2). Your goal is to create concise, highly relevant vocabulary content with clearly distinguishable sense definitions."""

STAGE3_DICT_FILTER_BATCH_PROMPT = """You are a bilingual lexicographer creating flashcards for Taiwanese high school students (GSAT Prep).
Your task is to take raw dictionary data and refine it into high-quality meaning clusters (typically 2-4 total).

### Core Principles:
1. **Preserve POS Diversity**: If a lemma has multiple parts of speech (e.g., both NOUN and VERB), you MUST preserve at least one high-quality cluster for EACH part of speech that appears in the context or is common. Never discard an entire POS category if it's relevant.
2. **Discard the Noise**: Actively remove senses that are archaic, technical, slang, or too rare for high school (CEFR A1-B2).
3. **Think in Chinese**: Group English senses based on whether they map to the same Chinese translation concept.
4. **Merge Similar Senses Aggressively**: If two senses would have nearly identical Chinese translations or only differ in subtle nuance, they MUST be merged into ONE cluster. Each cluster must be clearly distinguishable from others. For example:
   - "available on the Internet" and "connected to the Internet" → merge into ONE cluster (both = 網路上的)
   - "coins used to buy things" and "wealth in general" → merge into ONE cluster (both = 金錢)
   - "deliver a package" vs "deliver a speech" → keep SEPARATE (遞送 vs 發表, clearly different)
5. **Comprehensive Polysemy (一字多義)**: Ensure senses found in the provided <contexts> are primary, but you MUST also include other common, distinct, and high-frequency senses from the dictionary data, even if they have not appeared in the provided contexts. We want to prepare students for ALL common usages of a word at the GSAT level (CEFR A1-B2), not just past exam occurrences.

### Output Requirements:
- For each lemma, return 1-4 clusters (prefer fewer, more distinct clusters over many similar ones).
- Each cluster MUST contain:
    - "pos": The specific Part of Speech (NOUN, VERB, ADJ, ADV, etc.)
    - "core_meaning": Format = "繁中定義 (English with distinctive keywords)"
      - The English part must use different vocabulary for each sense
      - Include collocations when helpful: "commit a crime" vs "commit to a cause"
      - Add context clues: "island (land surrounded by water)" vs "island (isolated area, e.g. traffic island)"

### Input Format:
The input is an XML block containing multiple <lemma> tags. Each lemma has its own <senses> and <contexts>.

### Example:
Input XML includes:
<lemma name="cook">
  <contexts>...cooking...</contexts>
  <senses>
    <sense id="s0" pos="NOUN">a person who prepares food</sense>
    <sense id="s1" pos="VERB">to prepare food by heating</sense>
  </senses>
</lemma>
<lemma name="commit">
  <contexts>...committed the crime...</contexts>
  <senses>
    <sense id="s0" pos="VERB">to do something illegal</sense>
    <sense id="s1" pos="VERB">to promise or dedicate</sense>
  </senses>
</lemma>

Expected JSON Output:
{{
  "items": [
    {{
      "lemma": "cook",
      "clusters": [
        {{
          "primary_id": "s0",
          "merged_ids": ["s0"],
          "pos": "NOUN",
          "core_meaning": "廚師 (a person who prepares food professionally)"
        }},
        {{
          "primary_id": "s1",
          "merged_ids": ["s1"],
          "pos": "VERB",
          "core_meaning": "烹飪 (to prepare food by heating)"
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
          "core_meaning": "犯（罪）(to do something illegal, e.g. commit a crime/murder)"
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

Input XML to process:
<lemmas>
{lemmas_xml}
</lemmas>

Return JSON only:"""

STAGE3_LLMS_DEFINE_SYSTEM = """You are a bilingual lexicographer specializing in high school English education (GSAT/CEFR A1-B2). Your goal is to create concise, highly relevant vocabulary content with clearly distinguishable sense definitions."""

STAGE3_LLMS_DEFINE_PROMPT = """You are a bilingual lexicographer creating flashcards for Taiwanese high school students (GSAT Prep).
Your task is to define the word "{lemma}" with 1-4 high-quality meaning clusters.

### Core Principles:
1. **Preserve POS Diversity**: If this word has multiple parts of speech (e.g., both NOUN and VERB), you MUST provide at least one cluster for EACH common POS. Never omit an entire POS category if it's relevant.
2. **Discard the Noise**: Do NOT include senses that are archaic, technical, slang, or too rare for high school level (CEFR A1-B2).
3. **Think in Chinese**: Group English senses based on whether they map to the same Chinese translation concept.
4. **Merge Similar Senses Aggressively**: If two senses would have nearly identical Chinese translations or only differ in subtle nuance, they MUST be merged into ONE cluster. Each cluster must be clearly distinguishable from others. Prefer fewer, more distinct clusters over many similar ones.
5. **Comprehensive Polysemy (一字多義)**: Prioritize senses found in the provided <contexts>, but also include other common, high-frequency senses even if not in the contexts. Prepare students for ALL common usages at GSAT level.

### Input:
POS hint: {pos}

Exam sentences where this word appeared:
<contexts>
{contexts_xml}
</contexts>

### Output Requirements:
Return 1-4 clusters. Each cluster MUST contain:
- "pos": The Part of Speech (NOUN, VERB, ADJ, ADV, etc.)
- "core_meaning": Format = "繁中定義 (English with distinctive keywords)"
  - Use different vocabulary for each sense
  - Include collocations: "commit a crime" vs "commit to a cause"
- "examples": 1-2 example sentences (optional)

### Example Output:
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
      "examples": ["She delivered an inspiring speech."]
    }}
  ]
}}

Return JSON only:"""

STAGE3_LLMS_DEFINE_PHRASE_PROMPT = """You are a bilingual lexicographer creating flashcards for Taiwanese high school students (GSAT Prep).
Your task is to define the phrase "{lemma}" with 1-4 high-quality meaning clusters.

### Core Principles:
1. **Discard the Noise**: Do NOT include senses that are archaic, technical, slang, or too rare for high school level (CEFR A1-B2).
2. **Think in Chinese**: Group English senses based on whether they map to the same Chinese translation concept.
3. **Merge Similar Senses Aggressively**: If two senses would have nearly identical Chinese translations or only differ in subtle nuance, they MUST be merged into ONE cluster. Each cluster must be clearly distinguishable from others. Prefer fewer, more distinct clusters over many similar ones.
4. **Comprehensive Polysemy (一字多義)**: Prioritize senses found in the provided <contexts>, but also include other common, high-frequency senses even if not in the contexts. Prepare students for ALL common usages at GSAT level.

### Input:
Exam sentences where this phrase appeared:
<contexts>
{contexts_xml}
</contexts>

### Output Requirements:
Return 1-4 clusters. Each cluster MUST contain:
- "core_meaning": Format = "繁中定義 (English with distinctive keywords)"
  - Use different vocabulary for each sense
  - Include usage context and examples when helpful
- "examples": 1-2 example sentences (optional)

NOTE: Phrases do NOT have a "pos" field since they are multi-word expressions.

### Example Output:
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

Return JSON only:"""

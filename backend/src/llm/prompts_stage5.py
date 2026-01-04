STAGE5_WSD_SYSTEM = """You are a word sense disambiguation expert for a vocabulary learning system. Your task is to match word usages in sentences to their correct dictionary definitions."""

STAGE5_WSD_BATCH_PROMPT = """For each item below, determine which sense best matches the word usage in context.

Rules:
- Return sense_index = 1, 2, 3... for the best matching sense
- Return sense_index = 0 ONLY when NONE of the provided senses apply, such as:
  - The word is part of a fixed expression (e.g., "order" in "in order to" has no standalone meaning)
  - The word is used in a completely different sense not listed
  - The context doesn't provide enough information to determine the sense

Most words WILL match one of the senses. Only use 0 for clear cases where no sense fits.

{items_xml}

Return JSON with your decisions:"""

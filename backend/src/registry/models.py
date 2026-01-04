from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegistrySense(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sense_id: str = Field(description="Stable identifier for this sense.")
    lemma: str
    pos: str | None = Field(
        default=None,
        description="Part of speech: NOUN, VERB, ADJ, ADV, or None for phrases/idioms.",
    )
    source: Literal["dictionaryapi", "llm_generated"] = Field(
        description="Origin of this sense definition."
    )
    definition: str = Field(description="Primary English definition/gloss for this sense.")


class SenseRegistry(BaseModel):
    version: str = Field(default="1.0.0", description="Registry format version for compatibility")

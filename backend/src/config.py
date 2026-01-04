from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"

    # Fast model for simple tasks (Stage 0, 4, simple batches)
    openai_model_fast: str = "gpt-4.1"
    # Balanced model for moderate complexity tasks
    openai_model_balanced: str = "gpt-5-mini"
    # Smart model for complex reasoning (Stage 1, 3, 6)
    openai_model_smart: str = "gpt-5.1"
    openai_embedding_model: str = "text-embedding-3-small"

    llm_output_mode_fast: Literal["json_schema", "tool_call"] = "json_schema"
    llm_output_mode_balanced: Literal["json_schema", "tool_call"] = "json_schema"
    llm_output_mode_smart: Literal["json_schema", "tool_call"] = "json_schema"

    llm_concurrency: int = 12
    llm_request_delay: float = 1.2  # seconds between requests

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

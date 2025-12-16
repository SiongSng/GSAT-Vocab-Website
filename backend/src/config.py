from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"

    # Fast model for simple tasks (Stage 0, 4, simple batches)
    openai_model_fast: str = "gpt-4.1"
    # Smart model for complex reasoning (Stage 1, 3, 6)
    openai_model_smart: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    llm_concurrency: int = 60
    llm_request_delay: float = 1.5  # seconds between requests

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

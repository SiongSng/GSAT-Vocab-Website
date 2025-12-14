import asyncio
import json
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel

from ..config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelTier(Enum):
    FAST = "fast"  # Simple tasks: uses Chat Completions API
    SMART = "smart"  # Complex reasoning: uses Responses API


def _add_additional_properties(schema: dict) -> dict:
    if schema.get("type") == "object":
        schema["additionalProperties"] = False
        if "properties" in schema:
            all_props = list(schema["properties"].keys())
            schema["required"] = all_props
            for prop in schema["properties"].values():
                _add_additional_properties(prop)
    if "items" in schema:
        _add_additional_properties(schema["items"])
    if "$defs" in schema:
        for definition in schema["$defs"].values():
            _add_additional_properties(definition)
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            _add_additional_properties(option)
    return schema


class LLMClient:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model_fast = settings.openai_model_fast
        self._model_smart = settings.openai_model_smart
        self._embedding_model = settings.openai_embedding_model
        self._concurrency = settings.llm_concurrency
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._request_delay = settings.llm_request_delay
        self._last_request_time = 0.0
        self._delay_lock = asyncio.Lock()

    def _get_model(self, tier: ModelTier) -> str:
        return self._model_fast if tier == ModelTier.FAST else self._model_smart

    async def _complete_chat(
        self,
        model: str,
        prompt: str,
        system: str,
        schema: dict,
        temperature: float,
    ) -> str:
        """Use Chat Completions API for FAST tier."""
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "output",
                    "strict": True,
                    "schema": schema,
                },
            },
        )
        return response.choices[0].message.content or ""

    async def _complete_responses(
        self,
        model: str,
        prompt: str,
        system: str,
        schema: dict,
        temperature: float,
    ) -> str:
        """Use Responses API for SMART tier."""
        response = await self._client.responses.create(
            model=model,
            input=prompt,
            instructions=system,
            reasoning={"effort": "none"},
            text={
                "format": {
                    "type": "json_schema",
                    "name": "output",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        return response.output_text or ""

    async def _wait_for_delay(self):
        async with self._delay_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self._request_delay:
                await asyncio.sleep(self._request_delay - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def complete(
        self,
        prompt: str,
        system: str,
        response_model: type[T],
        temperature: float = 0.2,
        max_retries: int = 5,
        tier: ModelTier = ModelTier.SMART,
    ) -> T:
        model = self._get_model(tier)
        schema = response_model.model_json_schema()
        schema.pop("title", None)
        schema.pop("description", None)
        _add_additional_properties(schema)

        async with self._semaphore:
            await self._wait_for_delay()
            for attempt in range(max_retries):
                try:
                    if tier == ModelTier.FAST:
                        content = await self._complete_chat(
                            model, prompt, system, schema, temperature
                        )
                    else:
                        content = await self._complete_responses(
                            model, prompt, system, schema, temperature
                        )

                    if not content:
                        raise ValueError("Empty response from LLM")
                    return response_model.model_validate_json(content)
                except RateLimitError:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(
                        f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(wait_time)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"LLM call failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2)
            raise RuntimeError("Max retries exceeded")

    async def get_embeddings(
        self, texts: list[str], max_retries: int = 3, batch_size: int = 300
    ) -> list[list[float]]:
        if not texts:
            return []

        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            async with self._semaphore:
                await self._wait_for_delay()
                for attempt in range(max_retries):
                    try:
                        response = await self._client.embeddings.create(
                            input=batch,
                            model=self._embedding_model,
                        )
                        results.extend([d.embedding for d in response.data])
                        break
                    except RateLimitError:
                        wait_time = 10 * (attempt + 1)
                        logger.warning(
                            f"Embedding rate limit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        await asyncio.sleep(wait_time)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            logger.error(f"Embedding failed after {max_retries} attempts: {e}")
                            raise
                        wait_time = 2 * (attempt + 1)
                        logger.warning(
                            f"Embedding failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        await asyncio.sleep(wait_time)

        return results

    async def complete_batch(
        self,
        items: list[Any],
        prompt_fn: Callable[[Any], str],
        system: str,
        response_model: type[T],
        temperature: float = 0.2,
    ) -> list[tuple[Any, T | None]]:
        async def process_item(item: Any) -> tuple[Any, T | None]:
            try:
                result = await self.complete(
                    prompt=prompt_fn(item),
                    system=system,
                    response_model=response_model,
                    temperature=temperature,
                )
                return item, result
            except Exception as e:
                logger.error(f"Failed to process item {item}: {e}")
                return item, None

        tasks = [process_item(item) for item in items]
        return await asyncio.gather(*tasks)


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

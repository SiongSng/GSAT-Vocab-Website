import asyncio
import contextlib
import json
import logging
import re
from collections.abc import Callable
from enum import Enum
from typing import Any, Literal, TypeVar

from openai import APIStatusError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from ..config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

OutputMode = Literal["json_schema", "tool_call"]


class ModelTier(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    SMART = "smart"


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


def _inline_refs(schema: dict, defs: dict | None = None) -> dict:
    """Inline all $ref references since Claude's tool API doesn't support $defs."""
    if defs is None:
        defs = schema.pop("$defs", {})

    if "$ref" in schema:
        ref_path = schema["$ref"]
        if ref_path.startswith("#/$defs/"):
            def_name = ref_path.split("/")[-1]
            if def_name in defs:
                inlined = defs[def_name].copy()
                return _inline_refs(inlined, defs)
        return schema

    result = {}
    for key, value in schema.items():
        if key == "$defs":
            continue
        elif isinstance(value, dict):
            result[key] = _inline_refs(value, defs)
        elif isinstance(value, list):
            result[key] = [
                _inline_refs(item, defs) if isinstance(item, dict) else item for item in value
            ]
        else:
            result[key] = value

    return result


def _extract_json_block(content: str) -> Any | None:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(cleaned)

    bracket_match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.S)
    if bracket_match:
        snippet = bracket_match.group(1)
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(snippet)

    return None


def _coerce_for_model(response_model: type[BaseModel], parsed: Any) -> Any | None:
    model_fields = getattr(response_model, "model_fields", {}) or {}
    expects_items = "items" in model_fields

    if isinstance(parsed, list) and expects_items:
        return {"items": parsed}

    if isinstance(parsed, dict):
        if expects_items and "items" in parsed and isinstance(parsed["items"], list):
            return {"items": parsed["items"]}

        for key in (
            "output",
            "result",
            "results",
            "data",
            "response",
            "parameter",
            "value",
            "values",
        ):
            if key in parsed:
                inner = parsed[key]
                if expects_items and isinstance(inner, list):
                    return {"items": inner}
                return inner

    return None


class LLMClient:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._model_fast = settings.openai_model_fast
        self._model_balanced = settings.openai_model_balanced
        self._model_smart = settings.openai_model_smart
        self._embedding_model = settings.openai_embedding_model
        self._output_mode_fast: OutputMode = settings.llm_output_mode_fast
        self._output_mode_balanced: OutputMode = settings.llm_output_mode_balanced
        self._output_mode_smart: OutputMode = settings.llm_output_mode_smart
        self._concurrency = settings.llm_concurrency
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._request_delay = settings.llm_request_delay
        self._dispatch_lock = asyncio.Lock()

    def _get_model(self, tier: ModelTier) -> str:
        if tier == ModelTier.FAST:
            return self._model_fast
        elif tier == ModelTier.BALANCED:
            return self._model_balanced
        else:
            return self._model_smart

    def _get_output_mode(self, tier: ModelTier) -> OutputMode:
        if tier == ModelTier.FAST:
            return self._output_mode_fast
        elif tier == ModelTier.BALANCED:
            return self._output_mode_balanced
        else:
            return self._output_mode_smart

    async def _complete_chat(
        self,
        model: str,
        prompt: str,
        system: str,
        schema: dict,
        temperature: float,
    ) -> str:
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

    async def _complete_tool_call(
        self,
        model: str,
        prompt: str,
        system: str,
        schema: dict,
        temperature: float,
    ) -> str:
        import json

        schema_message = f"Your output MUST conform to this schema. For enum fields, use ONLY the listed values.\n\n```json\n{json.dumps(schema, indent=2)}\n```"

        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": schema_message},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "output",
                        "strict": True,
                        "parameters": schema,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "output"}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError("No tool call in response")
        return tool_calls[0].function.arguments

    async def _dispatch(self):
        async with self._dispatch_lock:
            await asyncio.sleep(self._request_delay)

    async def complete(
        self,
        prompt: str,
        system: str,
        response_model: type[T],
        temperature: float = 0.2,
        max_retries: int = 5,
        tier: ModelTier = ModelTier.SMART,
        output_mode: OutputMode | None = None,
    ) -> T:
        model = self._get_model(tier)
        schema = response_model.model_json_schema()
        schema.pop("title", None)
        schema.pop("description", None)
        _add_additional_properties(schema)

        prompt_with_cot = prompt
        mode = output_mode or self._get_output_mode(tier)

        # Claude's tool API doesn't support $defs/$ref - inline all references
        if mode == "tool_call":
            schema = _inline_refs(schema)

        async with self._semaphore:
            await self._dispatch()
            for attempt in range(max_retries):
                try:
                    if mode == "tool_call":
                        content = await self._complete_tool_call(
                            model, prompt_with_cot, system, schema, temperature
                        )
                    else:
                        content = await self._complete_chat(
                            model, prompt_with_cot, system, schema, temperature
                        )

                    if not content:
                        raise ValueError("Empty response from LLM")
                    try:
                        return response_model.model_validate_json(content)
                    except ValidationError:
                        parsed = _extract_json_block(content)
                        if parsed is not None:
                            with contextlib.suppress(ValidationError):
                                return response_model.model_validate(parsed)
                            coerced = _coerce_for_model(response_model, parsed)
                            if coerced is not None:
                                with contextlib.suppress(ValidationError):
                                    logger.warning(
                                        "LLM response coerced for %s", response_model.__name__
                                    )
                                    return response_model.model_validate(coerced)
                        raise
                except RateLimitError:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(
                        f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(wait_time)
                except APIStatusError as e:
                    if e.status_code >= 500:
                        wait_time = 5 * (attempt + 1)
                        logger.warning(
                            f"Server error {e.status_code}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        if attempt == max_retries - 1:
                            raise
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"LLM call failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2)
            raise RuntimeError("Max retries exceeded")

    async def _get_embedding_batch(
        self, batch: list[str], batch_idx: int, max_retries: int = 3
    ) -> tuple[int, list[list[float]]]:
        async with self._semaphore:
            await self._dispatch()
            for attempt in range(max_retries):
                try:
                    response = await self._client.embeddings.create(
                        input=batch,
                        model=self._embedding_model,
                    )
                    return batch_idx, [d.embedding for d in response.data]
                except RateLimitError:
                    wait_time = 10 * (attempt + 1)
                    logger.warning(
                        f"Embedding batch {batch_idx} rate limit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Embedding batch {batch_idx} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    wait_time = 2 * (attempt + 1)
                    logger.warning(
                        f"Embedding batch {batch_idx} failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(wait_time)
            raise RuntimeError(f"Embedding batch {batch_idx} max retries exceeded")

    async def get_embeddings(
        self, texts: list[str], max_retries: int = 3, batch_size: int = 300
    ) -> list[list[float]]:
        if not texts:
            return []

        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        if len(batches) == 1:
            _, embeddings = await self._get_embedding_batch(batches[0], 0, max_retries)
            return embeddings

        tasks = [
            self._get_embedding_batch(batch, idx, max_retries) for idx, batch in enumerate(batches)
        ]
        batch_results = await asyncio.gather(*tasks)

        batch_results_sorted = sorted(batch_results, key=lambda x: x[0])
        results: list[list[float]] = []
        for _, embeddings in batch_results_sorted:
            results.extend(embeddings)

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

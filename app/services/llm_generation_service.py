import configparser
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional, TypeVar, Union

from app.core.cache import hash_cache_key, llm_structured_cache, llm_text_cache
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel

from app.core.config import settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LLM_CONFIG_PATH = _REPO_ROOT / "config" / "llm.config.ini"
_LLM_CONFIG_PATH = os.getenv("LLM_CONFIG_FILE", str(_DEFAULT_LLM_CONFIG_PATH))

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def _load_llm_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not cfg.read(_LLM_CONFIG_PATH):
        raise FileNotFoundError(f"LLM config file not found: {_LLM_CONFIG_PATH}")
    return cfg


def _get_chat_model_name() -> str:
    env_override = os.getenv("LLM_MODEL_NAME")
    if env_override:
        return env_override
    cfg = _load_llm_config()
    return cfg.get("llm", "model_name", fallback="").strip()


def _get_embeddings_model_name() -> str:
    env_override = os.getenv("EMBEDDINGS_MODEL_NAME")
    if env_override:
        return env_override
    cfg = _load_llm_config()
    return cfg.get("embeddings", "model_name", fallback="").strip()


def _get_openai_client() -> OpenAI:
    """
    Get an authenticated OpenAI client using OpenRouter.

    Returns:
        OpenAI client instance

    Raises:
        ValueError: If the API token is not set
    """
    api_token: str = settings.OPEN_ROUTER_API_KEY

    if not api_token:
        raise ValueError("API token is not set.")

    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_token)


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    if "rate limit" in message or "free-models-per-min" in message:
        return True
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    return False


def _with_retries(fn: Callable[[], T]) -> T:
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    base_delay = float(os.getenv("LLM_RETRY_BASE_SECONDS", "1.0"))
    max_delay = float(os.getenv("LLM_RETRY_MAX_SECONDS", "10.0"))

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit_error(exc) or attempt == max_retries:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            time.sleep(delay)

    if last_exc:
        raise last_exc
    raise RuntimeError("LLM call failed without exception")


def make_llm_call_text_generation(user_prompt: str, system_prompt: str) -> str:
    model_name = _get_chat_model_name()
    if not model_name:
        raise ValueError("LLM model name is not set.")

    cache_key = hash_cache_key("llm_text", model_name, system_prompt, user_prompt)
    cached = llm_text_cache.get(cache_key)
    if cached is not None:
        return cached

    messages: list[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    client = _get_openai_client()
    completion = _with_retries(
        lambda: client.chat.completions.create(model=model_name, messages=messages)
    )
    content = completion.choices[0].message.content
    logger.info("Text generation response received")
    if content is not None:
        llm_text_cache.set(cache_key, content)
    return content


def make_llm_call_structured_output_generic(
    user_prompt: str,
    system_prompt: str,
    model_class: type[T],
    schema_name: str = "response_schema",
) -> tuple[Optional[T], Optional[str]]:
    """
    Generic function for making LLM calls that return structured data.

    Args:
        user_prompt: The prompt to send to the LLM
        system_prompt: The system prompt that guides LLM behavior
        model_class: The Pydantic model class to use for the response
        schema_name: The name to use for the schema in the response format

    Returns:
        A tuple of (result, error_message). If successful,
        result contains the model instance and error_message is None.
        If failed, result is None and error_message contains the error.
    """
    try:
        model_name = _get_chat_model_name()
        if not model_name:
            raise ValueError("LLM model name is not set.")

        schema = model_class.model_json_schema()
        schema_fingerprint = json.dumps(schema, sort_keys=True)
        cache_key = hash_cache_key(
            "llm_structured",
            model_name,
            system_prompt,
            user_prompt,
            schema_name,
            model_class.__module__,
            model_class.__name__,
            schema_fingerprint,
        )
        cached = llm_structured_cache.get(cache_key)
        if cached is not None:
            try:
                return model_class.model_validate(cached), None
            except Exception as exc:
                logger.warning(
                    "Cached structured response failed validation; evicting. Error: %s",
                    exc,
                )
                llm_structured_cache.delete(cache_key)

        client = _get_openai_client()

        response_format = ResponseFormatJSONSchema(
            type="json_schema",
            json_schema={"name": schema_name, "schema": schema},
        )

        # Call with proper JSON schema format
        completion = _with_retries(
            lambda: client.chat.completions.create(
                model=model_name,
                messages=[
                    ChatCompletionSystemMessageParam(
                        role="system", content=system_prompt
                    ),
                    ChatCompletionUserMessageParam(role="user", content=user_prompt),
                ],
                response_format=response_format,
                max_tokens=1000,
            )
        )

        content = completion.choices[0].message.content
        logger.info(f"Structured output response: {content!r}")

        # Parse the JSON response

        try:
            response_data = json.loads(content)
            result = model_class.model_validate(response_data)
            llm_structured_cache.set(cache_key, result.model_dump())
            return result, None
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}. Raw content: {content!r}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Failed to validate response data: {e}"
            logger.error(error_msg)
            return None, error_msg

    except Exception as e:
        error_msg = f"LLM API call failed: {e}"
        logger.error(error_msg)
        return None, error_msg


def make_embedding(text: str) -> list[float]:
    model_name = _get_embeddings_model_name()
    if not model_name:
        raise ValueError("Embeddings model name is not set.")

    client = _get_openai_client()
    response = _with_retries(
        lambda: client.embeddings.create(model=model_name, input=text)
    )
    return response.data[0].embedding

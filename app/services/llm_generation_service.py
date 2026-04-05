import json
import logging
import time
from collections.abc import Iterator
from typing import Any, Callable, Optional, TypeVar, Union

from app.core.cache import hash_cache_key, llm_structured_cache, llm_text_cache
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel

from app.core.config import settings
from app.core.tracing import log_span, start_trace_span

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def _get_chat_model_name() -> str:
    return settings.LLM_MODEL_NAME


def _get_embeddings_model_name() -> str:
    return settings.EMBEDDINGS_MODEL_NAME


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
    max_retries = settings.LLM_MAX_RETRIES
    base_delay = settings.LLM_RETRY_BASE_SECONDS
    max_delay = settings.LLM_RETRY_MAX_SECONDS

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


def _usage_to_metrics(usage: object | None) -> dict[str, int]:
    if usage is None:
        return {}

    metrics: dict[str, int] = {}
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    if isinstance(prompt_tokens, int):
        metrics["prompt_tokens"] = prompt_tokens
    if isinstance(completion_tokens, int):
        metrics["completion_tokens"] = completion_tokens
    if isinstance(total_tokens, int):
        metrics["tokens"] = total_tokens
    return metrics


def _text_prompt_summary(
    user_prompt: str,
    system_prompt: str,
) -> dict[str, int]:
    return {
        "user_prompt_chars": len(user_prompt),
        "system_prompt_chars": len(system_prompt),
    }


def _text_prompt_payload(
    user_prompt: str,
    system_prompt: str,
) -> dict[str, list[dict[str, str]]]:
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    }


def _assistant_output_payload(content: str | None) -> dict[str, list[dict[str, str]]]:
    return {
        "messages": [
            {
                "role": "assistant",
                "content": content or "",
            }
        ]
    }


def _coerce_content_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, (bytes, bytearray)):
        return content.decode("utf-8", errors="replace")
    if not isinstance(content, list):
        return None

    parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            text = part
        elif isinstance(part, dict):
            text = part.get("text")
            if not isinstance(text, str) and isinstance(text, dict):
                value = text.get("value")
                text = value if isinstance(value, str) else None
        else:
            text = getattr(part, "text", None)
            if not isinstance(text, str):
                value = getattr(text, "value", None)
                text = value if isinstance(value, str) else None

        if isinstance(text, str) and text:
            parts.append(text)

    if not parts:
        return None
    return "".join(parts)


def _extract_structured_content_text(message: Any) -> str | None:
    content_text = _coerce_content_text(getattr(message, "content", None))
    if content_text is not None:
        return content_text

    parsed_payload = getattr(message, "parsed", None)
    if parsed_payload is not None:
        if isinstance(parsed_payload, BaseModel):
            parsed_payload = parsed_payload.model_dump()
        try:
            return json.dumps(parsed_payload, ensure_ascii=True)
        except TypeError:
            return str(parsed_payload)

    function_call = getattr(message, "function_call", None)
    function_args = getattr(function_call, "arguments", None)
    if isinstance(function_args, str) and function_args.strip():
        return function_args

    tool_calls = getattr(message, "tool_calls", None)
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            if function is None and isinstance(tool_call, dict):
                function = tool_call.get("function")

            arguments = getattr(function, "arguments", None)
            if arguments is None and isinstance(function, dict):
                arguments = function.get("arguments")

            if isinstance(arguments, str) and arguments.strip():
                return arguments

    return None


def make_llm_call_text_generation(user_prompt: str, system_prompt: str) -> str:
    model_name = _get_chat_model_name()
    if not model_name:
        raise ValueError("LLM model name is not set.")

    cache_key = hash_cache_key("llm_text", model_name, system_prompt, user_prompt)
    prompt_summary = _text_prompt_summary(user_prompt, system_prompt)
    prompt_payload = _text_prompt_payload(user_prompt, system_prompt)

    with start_trace_span(
        name="llm.text_generation",
        span_type="llm",
        input_data=prompt_payload,
        metadata={
            "model": model_name,
            "cache_key": cache_key,
            "stream": False,
            **prompt_summary,
        },
    ) as span:
        cached = llm_text_cache.get(cache_key)
        if cached is not None:
            log_span(
                span,
                output={
                    **_assistant_output_payload(cached),
                    "content": cached,
                    "content_chars": len(cached),
                },
                metadata={"cache_hit": True},
            )
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

        usage_metrics = _usage_to_metrics(getattr(completion, "usage", None))
        log_span(
            span,
            output={
                **_assistant_output_payload(content),
                "content": content,
                "content_chars": len(content or ""),
            },
            metadata={"cache_hit": False},
            metrics=usage_metrics,
        )

        if content is not None:
            llm_text_cache.set(cache_key, content)
        return content


def stream_llm_call_text_generation(
    user_prompt: str,
    system_prompt: str,
) -> Iterator[str]:
    model_name = _get_chat_model_name()
    if not model_name:
        raise ValueError("LLM model name is not set.")

    cache_key = hash_cache_key("llm_text", model_name, system_prompt, user_prompt)
    prompt_summary = _text_prompt_summary(user_prompt, system_prompt)
    prompt_payload = _text_prompt_payload(user_prompt, system_prompt)

    with start_trace_span(
        name="llm.text_generation.stream",
        span_type="llm",
        input_data=prompt_payload,
        metadata={
            "model": model_name,
            "cache_key": cache_key,
            "stream": True,
            **prompt_summary,
        },
    ) as span:
        cached = llm_text_cache.get(cache_key)
        if cached is not None:
            log_span(
                span,
                output={
                    **_assistant_output_payload(cached),
                    "content": cached,
                    "content_chars": len(cached),
                },
                metadata={"cache_hit": True},
            )
            yield cached
            return

        messages: list[
            Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
        ] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            ChatCompletionUserMessageParam(role="user", content=user_prompt),
        ]

        client = _get_openai_client()
        stream = _with_retries(
            lambda: client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
            )
        )

        parts: list[str] = []
        chunk_count = 0
        stream_completed = False
        stream_interrupted = False
        stream_error: str | None = None

        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if not text:
                    continue
                chunk_count += 1
                parts.append(text)
                yield text
            stream_completed = True
        except GeneratorExit:
            stream_interrupted = True
            stream_error = "stream closed before completion"
            raise
        except Exception as exc:
            stream_error = str(exc)
            raise
        finally:
            content = "".join(parts)
            if stream_completed and content:
                llm_text_cache.set(cache_key, content)

            span_metadata: dict[str, Any] = {
                "cache_hit": False,
                "stream_completed": stream_completed,
            }
            if stream_interrupted:
                span_metadata["stream_interrupted"] = True
            if stream_error:
                span_metadata["stream_error"] = stream_error

            log_span(
                span,
                output={
                    **_assistant_output_payload(content),
                    "content": content,
                    "content_chars": len(content),
                    "chunk_count": chunk_count,
                },
                metadata=span_metadata,
            )


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
    span_metadata: dict[str, Any] = {
        "schema_name": schema_name,
        "model_class": f"{model_class.__module__}.{model_class.__name__}",
    }
    span_input = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "schema_name": schema_name,
    }
    prompt_summary = _text_prompt_summary(user_prompt, system_prompt)

    with start_trace_span(
        name="llm.structured_output",
        span_type="llm",
        input_data=span_input,
        metadata={**span_metadata, **prompt_summary},
    ) as span:
        try:
            model_name = _get_chat_model_name()
            if not model_name:
                raise ValueError("LLM model name is not set.")
            span_metadata["model"] = model_name

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
            span_metadata["cache_key"] = cache_key

            cached = llm_structured_cache.get(cache_key)
            if cached is not None:
                try:
                    result = model_class.model_validate(cached)
                    cached_payload = result.model_dump()
                    cached_content = json.dumps(
                        cached_payload,
                        ensure_ascii=True,
                        sort_keys=True,
                    )
                    log_span(
                        span,
                        output={
                            "success": True,
                            "cache_hit": True,
                            **_assistant_output_payload(cached_content),
                            "content": cached_content,
                            "response": cached_payload,
                        },
                        metadata={"cache_hit": True},
                    )
                    return result, None
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
            max_attempts = settings.LLM_STRUCTURED_OUTPUT_MAX_ATTEMPTS
            base_max_tokens = max(1, settings.LLM_STRUCTURED_MAX_TOKENS)
            last_error_msg: Optional[str] = None

            for attempt in range(1, max_attempts + 1):
                attempt_max_tokens = base_max_tokens * attempt

                completion = _with_retries(
                    lambda: client.chat.completions.create(
                        model=model_name,
                        messages=[
                            ChatCompletionSystemMessageParam(
                                role="system", content=system_prompt
                            ),
                            ChatCompletionUserMessageParam(
                                role="user", content=user_prompt
                            ),
                        ],
                        response_format=response_format,
                        max_tokens=attempt_max_tokens,
                    )
                )

                usage_metrics = _usage_to_metrics(getattr(completion, "usage", None))

                if not completion.choices:
                    error_msg = "LLM API returned no choices for structured output."
                    logger.error(error_msg)
                    last_error_msg = error_msg
                    if attempt < max_attempts:
                        logger.warning(
                            "Retrying structured output after empty choices "
                            "(attempt %s/%s).",
                            attempt + 1,
                            max_attempts,
                        )
                        continue
                    log_span(
                        span,
                        output={
                            "success": False,
                            "attempt": attempt,
                            **_assistant_output_payload(None),
                            "response": None,
                        },
                        metadata={"cache_hit": False, "error": error_msg},
                        metrics=usage_metrics,
                    )
                    return None, error_msg

                choice = completion.choices[0]
                message = choice.message
                content = message.content
                content_text = _extract_structured_content_text(message)
                logger.info(
                    "Structured output response (attempt %s/%s): %r",
                    attempt,
                    max_attempts,
                    content_text,
                )

                if content_text is None:
                    refusal = getattr(message, "refusal", None)
                    finish_reason = getattr(choice, "finish_reason", None)
                    has_tool_calls = bool(
                        getattr(message, "tool_calls", None)
                        or getattr(message, "function_call", None)
                    )
                    error_parts = ["Model returned no JSON content."]
                    if refusal:
                        error_parts.append(f"Refusal: {refusal}")
                    if finish_reason:
                        error_parts.append(f"finish_reason={finish_reason}")
                    if has_tool_calls:
                        error_parts.append(
                            "Response contained tool calls instead of content."
                        )
                    error_msg = " ".join(error_parts)
                    logger.error(error_msg)
                    last_error_msg = error_msg
                    if refusal:
                        log_span(
                            span,
                            output={
                                "success": False,
                                "attempt": attempt,
                                **_assistant_output_payload(None),
                                "response": None,
                            },
                            metadata={"cache_hit": False, "error": error_msg},
                            metrics=usage_metrics,
                        )
                        return None, error_msg
                    if attempt < max_attempts:
                        logger.warning(
                            "Retrying structured output after missing content "
                            "(attempt %s/%s). finish_reason=%s",
                            attempt + 1,
                            max_attempts,
                            finish_reason,
                        )
                        continue
                    log_span(
                        span,
                        output={
                            "success": False,
                            "attempt": attempt,
                            **_assistant_output_payload(None),
                            "response": None,
                        },
                        metadata={"cache_hit": False, "error": error_msg},
                        metrics=usage_metrics,
                    )
                    return None, error_msg

                try:
                    response_data = json.loads(content_text)
                    result = model_class.model_validate(response_data)
                    llm_structured_cache.set(cache_key, result.model_dump())
                    log_span(
                        span,
                        output={
                            "success": True,
                            "attempt": attempt,
                            **_assistant_output_payload(content_text),
                            "content": content_text,
                            "response": response_data,
                        },
                        metadata={"cache_hit": False},
                        metrics=usage_metrics,
                    )
                    return result, None
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse JSON response: {e}. Raw content: {content_text!r}"
                    logger.error(error_msg)
                    last_error_msg = error_msg
                    if attempt < max_attempts:
                        logger.warning(
                            "Retrying structured output after JSON parse failure "
                            "(attempt %s/%s).",
                            attempt + 1,
                            max_attempts,
                        )
                        continue
                    log_span(
                        span,
                        output={
                            "success": False,
                            "attempt": attempt,
                            **_assistant_output_payload(content_text),
                            "response": content_text,
                        },
                        metadata={"cache_hit": False, "error": error_msg},
                        metrics=usage_metrics,
                    )
                    return None, error_msg
                except Exception as e:
                    error_msg = f"Failed to validate response data: {e}"
                    logger.error(error_msg)
                    last_error_msg = error_msg
                    if attempt < max_attempts:
                        logger.warning(
                            "Retrying structured output after validation failure "
                            "(attempt %s/%s).",
                            attempt + 1,
                            max_attempts,
                        )
                        continue
                    log_span(
                        span,
                        output={
                            "success": False,
                            "attempt": attempt,
                            **_assistant_output_payload(
                                json.dumps(
                                    response_data, default=str, ensure_ascii=True
                                )
                            ),
                            "response": response_data,
                        },
                        metadata={"cache_hit": False, "error": error_msg},
                        metrics=usage_metrics,
                    )
                    return None, error_msg

            final_error = last_error_msg or "Structured output failed without an error"
            log_span(
                span,
                output={
                    "success": False,
                    **_assistant_output_payload(None),
                    "response": None,
                },
                metadata={"cache_hit": False, "error": final_error},
            )
            return None, final_error

        except Exception as e:
            error_msg = f"LLM API call failed: {e}"
            logger.error(error_msg)
            log_span(span, error=error_msg)
            return None, error_msg


def make_embedding(text: str) -> list[float]:
    model_name = _get_embeddings_model_name()
    if not model_name:
        raise ValueError("Embeddings model name is not set.")

    with start_trace_span(
        name="llm.embedding",
        span_type="llm",
        input_data={"text": text},
        metadata={"model": model_name, "input_chars": len(text)},
    ) as span:
        client = _get_openai_client()
        response = _with_retries(
            lambda: client.embeddings.create(model=model_name, input=text)
        )
        embedding = response.data[0].embedding
        usage_metrics = _usage_to_metrics(getattr(response, "usage", None))
        log_span(
            span,
            output={"embedding": embedding, "embedding_dimensions": len(embedding)},
            metrics=usage_metrics,
        )
        return embedding

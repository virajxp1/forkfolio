import configparser
import json
import logging
import os
from typing import Optional, TypeVar, Union

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel

from app.core.config import settings

_LLM_CONFIG_PATH = os.getenv("LLM_CONFIG_FILE", "config/llm.config.ini")

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


def make_llm_call_text_generation(user_prompt: str, system_prompt: str) -> str:
    messages: list[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    client = _get_openai_client()
    model_name = _get_chat_model_name()
    if not model_name:
        raise ValueError("LLM model name is not set.")

    completion = client.chat.completions.create(model=model_name, messages=messages)

    print(completion.choices[0].message.content)
    return completion.choices[0].message.content


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
    messages: list[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    try:
        client = _get_openai_client()

        # Get the JSON schema from the provided model class
        schema = model_class.model_json_schema()

        response_format = ResponseFormatJSONSchema(
            type="json_schema",
            json_schema={"name": schema_name, "schema": schema},
        )

        # Call with proper JSON schema format
        model_name = _get_chat_model_name()
        if not model_name:
            raise ValueError("LLM model name is not set.")

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format=response_format,
            max_tokens=1000,
        )

        content = completion.choices[0].message.content
        logger.info(f"Structured output response: {content!r}")

        # Parse the JSON response

        try:
            response_data = json.loads(content)
            result = model_class.model_validate(response_data)
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
    response = client.embeddings.create(model=model_name, input=text)
    return response.data[0].embedding

import json
from typing import TypeVar, Union

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel

from app.core.config import settings

model_name = "meta-llama/llama-4-maverick:free"

T = TypeVar("T", bound=BaseModel)


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
    completion = client.chat.completions.create(model=model_name, messages=messages)

    print(completion.choices[0].message.content)
    return completion.choices[0].message.content


def make_llm_call_structured_output_generic(
    user_prompt: str,
    system_prompt: str,
    model_class: type[T],
    schema_name: str = "response_schema",
) -> T:
    """
    Generic function for making LLM calls that return structured data.

    Args:
        user_prompt: The prompt to send to the LLM
        system_prompt: The system prompt that guides LLM behavior
        model_class: The Pydantic model class to use for the response
        schema_name: The name to use for the schema in the response format

    Returns:
        An instance of the provided model_class with data from the LLM response
    """
    messages: list[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    # Get the JSON schema from the provided model class
    schema = model_class.model_json_schema()

    # Create the response_format object
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": schema_name, "strict": True, "schema": schema},
    }

    client = _get_openai_client()

    # Call with the response_format
    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format=response_format,
        extra_body={"provider": {"require_parameters": True}},
    )

    # Parse the JSON response
    content = completion.choices[0].message.content
    response_data = json.loads(content)

    # Create and return an instance of the model class
    return model_class.model_validate(response_data)

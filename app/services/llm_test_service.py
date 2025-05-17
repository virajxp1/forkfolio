import json
from typing import Union

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.core.config import settings
from app.schemas.location_info import LocationInfo

model_name = "meta-llama/llama-4-maverick:free"


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


def make_llm_call_structured_output() -> LocationInfo:
    user_prompt: str = "Tell me about the city of Tokyo"
    system_prompt: str = (
        "You are a helpful assistant that provides information about locations."
    )

    messages: list[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    # Get the JSON schema from the LocationInfo model
    schema = LocationInfo.model_json_schema()

    # Create the response_format object as shown in the documentation
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "location_info", "strict": True, "schema": schema},
    }

    client = _get_openai_client()

    # Call with the response_format according to the documentation
    completion = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format=response_format,
        extra_body={"provider": {"require_parameters": True}},
    )

    # Parse the JSON response
    content = completion.choices[0].message.content
    location_data = json.loads(content)
    return LocationInfo(**location_data)

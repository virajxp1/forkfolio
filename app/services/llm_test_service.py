from typing import List, Union

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from app.core.config import settings

model_name = "deepseek/deepseek-r1-distill-llama-70b:free"


def make_llm_call() -> str:
    user_prompt: str = "What is the capital of France?"
    system_prompt: str = (
        "You are a helpful assistant. Always answer questions accurately and concise."
    )

    api_token: str = settings.OPEN_ROUTER_API_KEY

    if not api_token:
        raise ValueError("API token is not set.")

    messages: List[
        Union[ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam]
    ] = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=user_prompt),
    ]

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_token)

    completion = client.chat.completions.create(model=model_name, messages=messages)

    print(completion.choices[0].message.content)
    return completion.choices[0].message.content

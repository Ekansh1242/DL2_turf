from __future__ import annotations
import os
from typing import TypeVar
from pydantic import BaseModel
from openai import AsyncOpenAI

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key.strip() == "sk-...":
            raise RuntimeError("OPENAI_API_KEY is not set. The AI booking agent needs it to run.")
        self._client = AsyncOpenAI(api_key=api_key)

    async def structured_call(self, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        completion = await self._client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_model,
        )
        return completion.choices[0].message.parsed


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client

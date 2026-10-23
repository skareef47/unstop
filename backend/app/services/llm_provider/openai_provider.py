"""
OpenAI LLM Provider Adapter
"""
import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from app.services.llm_provider.base import BaseLLMProvider
from app.core.config import settings
from app.core.errors import ProviderException


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model or "gpt-4o-mini"
        if not self.api_key:
            raise ProviderException("openai", "OPENAI_API_KEY is not configured")

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            for msg in messages:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise ProviderException("openai", str(e))

    def generate_structured_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                response_format=schema,
            )
            parsed = response.choices[0].message.parsed
            if parsed:
                return parsed.model_dump()
            return {}
        except Exception as e:
            raise ProviderException("openai", str(e))

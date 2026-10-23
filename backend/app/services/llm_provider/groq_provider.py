"""
Groq LLM Provider Adapter
"""
import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from app.services.llm_provider.base import BaseLLMProvider
from app.core.config import settings
from app.core.errors import ProviderException


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model or "llama-3.3-70b-versatile"
        if not self.api_key:
            raise ProviderException("groq", "GROQ_API_KEY is not configured")

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)
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
            raise ProviderException("groq", str(e))

    def generate_structured_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)
            schema_json = json.dumps(schema.model_json_schema())
            instruction = f"{system_prompt or ''}\nYou must output valid JSON matching this schema:\n{schema_json}"

            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            return {}
        except Exception as e:
            raise ProviderException("groq", str(e))

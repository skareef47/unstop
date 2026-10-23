"""
Gemini LLM Provider Adapter
"""
import json
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from app.services.llm_provider.base import BaseLLMProvider
from app.core.config import settings
from app.core.errors import ProviderException


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.DEFAULT_LLM_MODEL or "gemini-2.5-flash"
        if not self.api_key:
            raise ProviderException("gemini", "GEMINI_API_KEY is not configured")

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            contents = []
            for msg in messages:
                contents.append(f"{msg['role'].upper()}: {msg['content']}")
            prompt = "\n".join(contents)

            config = types.GenerateContentConfig(
                temperature=temperature,
                system_instruction=system_prompt,
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            raise ProviderException("gemini", str(e))

    def generate_structured_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=system_prompt,
            )
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            if response.text:
                return json.loads(response.text)
            return {}
        except Exception as e:
            raise ProviderException("gemini", str(e))

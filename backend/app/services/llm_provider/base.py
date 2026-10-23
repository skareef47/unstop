"""
Base LLM Provider Interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class BaseLLMProvider(ABC):
    """Abstract LLM adapter to allow swapping Gemini, OpenAI, Groq, or Mock."""

    @abstractmethod
    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate conversational response given message history."""
        pass

    @abstractmethod
    def generate_structured_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured response validated against a Pydantic schema."""
        pass

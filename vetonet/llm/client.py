"""
LLM Client abstraction for VetoNet.

Supports multiple backends (Ollama, Anthropic) with a unified interface.
"""

import requests
from abc import ABC, abstractmethod
from typing import Any

from vetonet.config import LLMConfig, DEFAULT_LLM_CONFIG
from vetonet.llm.json_utils import extract_json_from_llm_response


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def query(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        pass

    @abstractmethod
    def query_json(self, prompt: str) -> dict[str, Any]:
        """Send a prompt and parse response as JSON."""
        pass


class OllamaClient(LLMClient):
    """
    Ollama client for local LLM inference.

    Runs completely on-device with no external API calls.
    """

    def __init__(self, config: LLMConfig = DEFAULT_LLM_CONFIG):
        self.config = config
        self.api_url = f"{config.base_url}/api/generate"

    def query(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        response = requests.post(
            self.api_url,
            json={
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                },
            },
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    def query_json(self, prompt: str) -> dict[str, Any]:
        """Send a prompt and parse response as JSON with secure parsing."""
        response_text = self.query(prompt)
        return extract_json_from_llm_response(response_text)


def create_client(config: LLMConfig = DEFAULT_LLM_CONFIG) -> LLMClient | None:
    """
    Factory function to create the appropriate LLM client.

    Supported providers:
        - "ollama": Local Ollama instance (default)
        - "groq": Groq API (free tier available)
        - "anthropic": Anthropic Claude API
        - "openai": OpenAI API
    """
    if config.provider == "ollama":
        return OllamaClient(config)

    elif config.provider == "groq":
        from vetonet.llm.groq import GroqClient

        if not config.api_key:
            raise ValueError("Groq provider requires api_key")
        return GroqClient(
            api_key=config.api_key,
            model=config.model,
            temperature=config.temperature,
        )

    elif config.provider == "anthropic":
        from vetonet.llm.anthropic import AnthropicClient

        if not config.api_key:
            raise ValueError("Anthropic provider requires api_key")
        return AnthropicClient(
            api_key=config.api_key,
            model=config.model,
            temperature=config.temperature,
        )

    elif config.provider == "openai":
        # OpenAI client - similar pattern
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI SDK not installed. Install with: pip install vetonet[openai]")
        if not config.api_key:
            raise ValueError("OpenAI provider requires api_key")

        # Create a simple OpenAI wrapper
        class OpenAIClient(LLMClient):
            def __init__(self, api_key, model, temperature):
                self.client = OpenAI(api_key=api_key)
                self.model = model
                self.temperature = temperature

            def query(self, prompt: str) -> str:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                )
                return response.choices[0].message.content

            def query_json(self, prompt: str) -> dict:
                response = self.query(prompt)
                return extract_json_from_llm_response(response)

        return OpenAIClient(
            api_key=config.api_key,
            model=config.model,
            temperature=config.temperature,
        )

    elif config.provider == "none":
        return None

    else:
        raise ValueError(
            f"Unsupported provider: {config.provider}. "
            f"Supported: ollama, groq, anthropic, openai, none"
        )

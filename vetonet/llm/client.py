"""
LLM Client abstraction for VetoNet.

Supports multiple backends (Ollama, Anthropic) with a unified interface.
"""

import json
import requests
from abc import ABC, abstractmethod
from typing import Any

from vetonet.config import LLMConfig, DEFAULT_LLM_CONFIG


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
        response_text = self.query(prompt).strip()

        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        # SECURITY: Use balanced brace extraction to prevent JSON injection
        json_obj = _extract_single_json_object(response_text)
        if json_obj is None:
            raise ValueError(f"No valid JSON found in response: {response_text[:100]}...")

        return json_obj


def _extract_single_json_object(text: str) -> dict | None:
    """
    Securely extract a single JSON object from text.
    Uses balanced brace counting to prevent injection attacks.
    """
    start_idx = text.find("{")
    if start_idx == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start_idx:], start_idx):
        if escape_next:
            escape_next = False
            continue

        if char == "\\" and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                # Found complete object
                json_str = text[start_idx : i + 1]
                try:
                    obj = json.loads(json_str)
                    # Validate it's a simple object (not nested deeply)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    return None
                return None

    return None


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
                # Extract JSON
                if response.strip().startswith("```"):
                    lines = response.strip().split("\n")
                    response = "\n".join(lines[1:-1])
                start = response.find("{")
                end = response.rfind("}") + 1
                return json.loads(response[start:end])

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

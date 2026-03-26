"""
Anthropic (Claude) LLM client for VetoNet.

Uses Claude for intent extraction and semantic matching.
Get your API key at: https://console.anthropic.com/
"""

import json
import re
from vetonet.llm.client import LLMClient


class AnthropicClient(LLMClient):
    """
    LLM client using Anthropic's Claude API.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        temperature: float = 0.1,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-haiku for cost efficiency)
            temperature: Sampling temperature (default: 0.1 for consistency)
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "Anthropic SDK not installed. Install with: pip install vetonet[anthropic]"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def query(self, prompt: str) -> str:
        """Send a prompt and get raw text response."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def query_json(self, prompt: str) -> dict:
        """Send a prompt and get parsed JSON response."""
        response = self.query(prompt)

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            response = json_match.group(1)

        # Clean up and parse
        response = response.strip()
        return json.loads(response)

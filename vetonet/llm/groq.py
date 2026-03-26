"""
Groq LLM client for VetoNet.

Groq provides free tier access to fast LLM inference.
Get your API key at: https://console.groq.com/
"""

import json
import re
from vetonet.llm.client import LLMClient


class GroqClient(LLMClient):
    """
    LLM client using Groq's API.

    Groq offers free tier with fast inference for Llama models.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        temperature: float = 0.1,
    ):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key from https://console.groq.com/
            model: Model to use (default: llama-3.1-8b-instant)
            temperature: Sampling temperature (default: 0.1 for consistency)
        """
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "Groq SDK not installed. Install with: pip install vetonet[groq]"
            )

        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def query(self, prompt: str) -> str:
        """Send a prompt and get raw text response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise assistant that extracts structured data. Always respond with valid JSON when asked."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=1024,
        )
        return response.choices[0].message.content

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

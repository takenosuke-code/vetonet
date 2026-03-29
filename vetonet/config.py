"""
Configuration and constants for VetoNet.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for the LLM backend."""
    provider: Literal["ollama", "groq", "anthropic", "openai", "none"] = "ollama"
    model: str = "qwen2.5:7b"
    base_url: str | None = "http://localhost:11434"
    api_key: str | None = None
    temperature: float = 0.1
    timeout: int = 120


@dataclass(frozen=True)
class VetoConfig:
    """Configuration for the Veto Engine."""
    # Price settings
    price_tolerance: float = 0.0  # Strict: no tolerance
    price_anomaly_threshold: float = 0.3  # Flag if < 30% of expected

    # Semantic settings
    semantic_threshold: float = 0.7  # Minimum similarity score

    # Vendor settings
    trusted_vendors: tuple[str, ...] = (
        "amazon.com",
        "walmart.com",
        "target.com",
        "bestbuy.com",
        "nike.com",
        "apple.com",
        "ebay.com",
        "costco.com",
        "footlocker.com",
    )

    suspicious_tlds: tuple[str, ...] = (
        # Original list
        ".ru", ".cn", ".tk", ".xyz",
        ".top", ".buzz", ".win", ".loan",
        # Added based on attack report (excluding .io - too many legit sites)
        ".cc", ".site", ".online", ".info",
        ".club", ".icu", ".work", ".click",
        ".gq", ".ml", ".cf", ".ga",  # Free TLDs often abused
    )


# Default configurations
DEFAULT_LLM_CONFIG = LLMConfig()
DEFAULT_VETO_CONFIG = VetoConfig()

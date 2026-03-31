"""
VetoNet - Semantic Firewall for AI Agent Transactions

A security layer that prevents AI agents from executing unauthorized
or manipulated transactions by validating intent-to-action alignment.
"""

__version__ = "0.1.2"
__author__ = "VetoNet"

from vetonet.models import IntentAnchor, AgentPayload, VetoResult, Fee
from vetonet.engine import VetoEngine
from vetonet.normalizer import IntentNormalizer
from vetonet.config import LLMConfig, VetoConfig
from vetonet.llm.client import create_client


class VetoNet:
    """
    High-level API for VetoNet verification.

    Simple one-liner interface for verifying AI agent transactions.

    Usage:
        veto = VetoNet()
        result = veto.verify("$50 Amazon Gift Card", {"item_description": "...", ...})

    Providers:
        - "ollama" (default): Local Ollama with qwen2.5:7b
        - "groq": Free hosted LLM (requires api_key)
        - "anthropic": Claude (requires api_key)
        - "openai": GPT-4 (requires api_key)
        - "none": Deterministic checks only, no LLM

    Classifier:
        - "local" (default): Use local ML classifier if available
        - "hosted": Call VetoNet API for classification (logs anonymized data)
        - "none": Skip ML classification

    Telemetry:
        - False (default): No telemetry
        - True: Send anonymized attack patterns to improve classifier
    """

    def __init__(
        self,
        provider: str = "ollama",
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        classifier: str = "local",
        telemetry: bool = False,
        **config_kwargs
    ):
        """
        Initialize VetoNet.

        Args:
            provider: LLM provider ("ollama", "groq", "anthropic", "openai", "none")
            model: Override default model for the provider
            api_key: API key for hosted providers (groq, anthropic, openai)
            base_url: Custom endpoint URL
            classifier: "local", "hosted", or "none"
            telemetry: Enable anonymous data collection (default False)
            **config_kwargs: Additional VetoConfig options
        """
        self.provider = provider
        self.classifier_mode = classifier
        self.telemetry_enabled = telemetry

        # Build LLM config
        default_models = {
            "ollama": "qwen2.5:7b",
            "groq": "llama-3.1-8b-instant",
            "anthropic": "claude-3-haiku-20240307",
            "openai": "gpt-4o-mini",
            "none": None,
        }

        self.llm_config = LLMConfig(
            provider=provider,
            model=model or default_models.get(provider, "qwen2.5:7b"),
            api_key=api_key,
            base_url=base_url or (
                "http://localhost:11434" if provider == "ollama" else None
            ),
        )

        # Build veto config
        self.veto_config = VetoConfig(**config_kwargs) if config_kwargs else VetoConfig()

        # Create LLM client (None for "none" provider)
        if provider == "none":
            self.llm_client = None
        else:
            self.llm_client = create_client(self.llm_config)

        # Create engine and normalizer
        self.engine = VetoEngine(
            veto_config=self.veto_config,
            llm_client=self.llm_client,
        )

        if self.llm_client:
            self.normalizer = IntentNormalizer(self.llm_client)
        else:
            self.normalizer = None

    def verify(
        self,
        intent: str | IntentAnchor,
        payload: dict | AgentPayload,
    ) -> VetoResult:
        """
        Verify a transaction against user intent.

        Args:
            intent: Natural language intent string OR structured IntentAnchor
            payload: Transaction payload dict OR AgentPayload object

        Returns:
            VetoResult with approval status and check details

        Raises:
            ValueError: If provider is "none" and intent is a string
        """
        # Normalize intent if it's a string
        if isinstance(intent, str):
            if self.normalizer is None:
                raise ValueError(
                    "Cannot normalize intent string with provider='none'. "
                    "Provide a structured IntentAnchor instead."
                )
            intent = self.normalizer.normalize(intent)

        # Convert payload dict to AgentPayload if needed
        if isinstance(payload, dict):
            # Handle fees if present
            fees = payload.get("fees", [])
            if fees and isinstance(fees[0], dict):
                payload["fees"] = [Fee(**f) for f in fees]

            # Use intent's category as default if not provided
            if "item_category" not in payload:
                payload["item_category"] = intent.item_category

            payload = AgentPayload(**payload)

        # Run the veto engine
        result = self.engine.check(intent, payload)

        # Log telemetry if enabled
        if self.telemetry_enabled:
            try:
                from vetonet.telemetry import log_telemetry
                log_telemetry(intent, payload, result)
            except Exception:
                pass  # Don't fail on telemetry errors

        return result

    def check(
        self,
        intent: IntentAnchor,
        payload: AgentPayload,
    ) -> VetoResult:
        """
        Low-level check with structured inputs.

        Same as verify() but requires structured IntentAnchor and AgentPayload.
        """
        return self.engine.check(intent, payload)


__all__ = [
    "VetoNet",
    "IntentAnchor",
    "AgentPayload",
    "VetoResult",
    "Fee",
    "VetoEngine",
    "IntentNormalizer",
    "LLMConfig",
    "VetoConfig",
]

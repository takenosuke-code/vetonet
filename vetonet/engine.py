"""
Veto Engine - The core of VetoNet.

Orchestrates all checks and produces the final veto decision.
"""

from vetonet.models import IntentAnchor, AgentPayload, VetoResult, VetoStatus, CheckResult
from vetonet.config import VetoConfig, LLMConfig, DEFAULT_VETO_CONFIG, DEFAULT_LLM_CONFIG
from vetonet.llm.client import LLMClient, create_client
from vetonet.checks import (
    check_price,
    check_category,
    check_currency,
    check_vendor,
    check_price_anomaly,
    check_quantity,
    check_hidden_fees,
    check_subscription_trap,
    check_currency_manipulation,
    check_semantic_match,
)


class VetoEngine:
    """
    The Veto Engine - semantic firewall for AI transactions.

    Performs a series of checks to validate that a transaction
    matches the user's original intent.

    Check order (fast to slow):
    1. Price check (deterministic)
    2. Quantity check (deterministic)
    3. Category check (deterministic)
    4. Currency manipulation check (deterministic)
    5. Subscription trap check (deterministic)
    6. Hidden fees check (deterministic)
    7. Vendor check (deterministic)
    8. Price anomaly check (deterministic)
    9. Semantic match (LLM-based)
    """

    def __init__(
        self,
        veto_config: VetoConfig = DEFAULT_VETO_CONFIG,
        llm_config: LLMConfig = DEFAULT_LLM_CONFIG,
        llm_client: LLMClient | None = None,
    ):
        self.veto_config = veto_config
        self.llm_client = llm_client or create_client(llm_config)

    def check(
        self,
        anchor: IntentAnchor,
        payload: AgentPayload,
    ) -> VetoResult:
        """
        Perform all checks and return the veto decision.

        Checks are performed in order from fastest to slowest.
        Fails fast on the first failed check.

        Args:
            anchor: The user's locked intent
            payload: The agent's proposed transaction

        Returns:
            VetoResult with decision and all check results
        """
        checks: list[CheckResult] = []

        # Run deterministic checks first (fast, free)
        deterministic_checks = [
            lambda: check_price(anchor, payload, self.veto_config),
            lambda: check_quantity(anchor, payload),
            lambda: check_category(anchor, payload),
            lambda: check_currency_manipulation(anchor, payload),
            lambda: check_subscription_trap(anchor, payload),
            lambda: check_hidden_fees(payload),
            lambda: check_vendor(payload, self.veto_config, anchor),
            lambda: check_price_anomaly(anchor, payload, self.veto_config),
        ]

        for check_fn in deterministic_checks:
            result = check_fn()
            checks.append(result)

            if not result.passed:
                return VetoResult(
                    status=VetoStatus.VETO,
                    reason=result.reason,
                    checks=checks,
                )

        # Run semantic check last (slower, uses LLM)
        if anchor.core_constraints:
            semantic_result = check_semantic_match(
                anchor,
                payload,
                self.llm_client,
                self.veto_config,
            )
            checks.append(semantic_result)

            if not semantic_result.passed:
                return VetoResult(
                    status=VetoStatus.VETO,
                    reason=f"Semantic check failed (score: {semantic_result.score:.2f}): {semantic_result.reason}",
                    checks=checks,
                )

        # All checks passed
        return VetoResult(
            status=VetoStatus.APPROVED,
            reason="All checks passed",
            checks=checks,
        )

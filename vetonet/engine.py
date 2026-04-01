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
    check_vendor,
    check_price_anomaly,
    check_quantity,
    check_hidden_fees,
    check_subscription_trap,
    check_currency_manipulation,
    check_scam_patterns,
    check_semantic_match,
)
from vetonet.checks.classifier import check_classifier, is_classifier_available


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
    9. Scam patterns check (deterministic)
    10. ML Classifier (fast CPU-based pre-filter)
    11. Semantic match (LLM-based, only for uncertain cases)
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
            lambda: check_scam_patterns(payload),
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

        # Run ML classifier check (fast, runs on CPU)
        # This is a pre-filter before the expensive LLM semantic check
        classifier_result = check_classifier(anchor, payload)

        if classifier_result is not None:
            checks.append(classifier_result)

            if not classifier_result.passed:
                # Classifier confidently detected an attack
                return VetoResult(
                    status=VetoStatus.VETO,
                    reason=classifier_result.reason,
                    checks=checks,
                )

            # Classifier confidently approved - skip LLM check
            if classifier_result.score and classifier_result.score >= 0.85:
                return VetoResult(
                    status=VetoStatus.APPROVED,
                    reason="ML classifier approved",
                    checks=checks,
                )

        # Run semantic check for uncertain cases (slower, uses LLM)
        # Always run if: classifier was uncertain OR transaction is high-value
        classifier_uncertain = classifier_result is None
        high_value = payload.unit_price >= 100  # $100+ transactions get extra scrutiny

        if anchor.core_constraints or classifier_uncertain or high_value:
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

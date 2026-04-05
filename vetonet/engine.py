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
    check_quantity,
    check_hidden_fees,
    check_subscription_trap,
    check_currency_manipulation,
    check_scam_patterns,
    check_crypto_substitution,
    check_market_value,
    check_semantic_match,
)
from vetonet.checks.classifier import check_classifier
import logging

logger = logging.getLogger(__name__)

_UNSET = object()


class VetoEngine:
    """
    The Veto Engine - semantic firewall for AI transactions.

    Performs a series of checks to validate that a transaction
    matches the user's original intent.

    Check order (fast to slow):
    1. Price check (deterministic) - total within budget
    2. Quantity check (deterministic)
    3. Category check (deterministic)
    4. Currency manipulation check (deterministic)
    5. Subscription trap check (deterministic)
    6. Hidden fees check (deterministic)
    7. Vendor check (deterministic)
    8. Scam patterns check (deterministic) - Nigerian prince, grandparent, etc.
    9. Market value check (deterministic) - $1 iPhone is always a scam
    10. Crypto substitution check (deterministic)
    11. ML Classifier (fast CPU-based pre-filter)
    12. Semantic match (LLM-based, only for uncertain cases)
    """

    def __init__(
        self,
        veto_config: VetoConfig = DEFAULT_VETO_CONFIG,
        llm_config: LLMConfig = DEFAULT_LLM_CONFIG,
        llm_client: LLMClient | None = _UNSET,
    ):
        self.veto_config = veto_config
        if llm_client is _UNSET:
            try:
                self.llm_client = create_client(llm_config)
            except Exception as e:
                logger.error("Failed to create LLM client: %s", e)
                if veto_config.semantic_mode == "always":
                    logger.critical(
                        "semantic_mode='always' but LLM client unavailable — "
                        "semantic checks will be skipped"
                    )
                self.llm_client = None
        else:
            self.llm_client = llm_client

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
            lambda: check_scam_patterns(payload),
            lambda: check_market_value(payload),
            lambda: check_crypto_substitution(anchor, payload),
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

        # Combo attack detection: accumulate suspicion from borderline passes
        accumulated_suspicion = sum(c.suspicion_weight for c in checks)
        nonzero_signals = sum(1 for c in checks if c.suspicion_weight > 0)
        if nonzero_signals >= 4:
            accumulated_suspicion *= 1.5
        elif nonzero_signals >= 3:
            accumulated_suspicion *= 1.3

        suspicion_force_semantic = False
        if accumulated_suspicion >= self.veto_config.suspicion_threshold:
            if self.veto_config.suspicion_shadow_mode:
                logger.warning(
                    "Suspicion score %.3f exceeds threshold %.3f (shadow mode)",
                    accumulated_suspicion,
                    self.veto_config.suspicion_threshold,
                )
            else:
                suspicion_force_semantic = True

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

        # Determine whether to run the semantic check
        run_semantic = False
        if self.veto_config.semantic_mode == "always":
            run_semantic = self.llm_client is not None
        elif self.veto_config.semantic_mode == "smart":
            classifier_uncertain = classifier_result is None
            high_value = payload.unit_price >= self.veto_config.semantic_skip_threshold
            run_semantic = self.llm_client is not None and (
                anchor.core_constraints or classifier_uncertain or high_value
            )
        # "never" -> run_semantic stays False

        # Suspicion scoring can force semantic check even in "smart"/"never" mode
        if suspicion_force_semantic and self.llm_client is not None:
            run_semantic = True

        if run_semantic:
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

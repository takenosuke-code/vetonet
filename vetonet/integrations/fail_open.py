"""Shared fail-open decision logic for VetoNet integrations."""

import logging
import os


def should_allow_fail_open(
    fail_open: bool,
    tool_name: str,
    error_type: str,
    logger: logging.Logger,
) -> bool:
    """Determine whether to allow execution when VetoNet verification fails.

    Requires BOTH fail_open=True in code AND VETONET_ALLOW_FAIL_OPEN=1 env var.
    Returns True only if both conditions are met. Handles all security logging.
    """
    if not fail_open:
        return False

    if os.environ.get("VETONET_ALLOW_FAIL_OPEN") == "1":
        logger.critical(
            "[SECURITY] Verification bypassed (%s) for %s — VETONET_ALLOW_FAIL_OPEN is set",
            error_type,
            tool_name,
        )
        return True

    logger.warning(
        "[SECURITY] fail_open=True for %s but VETONET_ALLOW_FAIL_OPEN not set — failing closed",
        tool_name,
    )
    return False

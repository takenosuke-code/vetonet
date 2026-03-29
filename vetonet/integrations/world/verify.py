"""
World ID verification for VetoNet.

Provides async and sync functions to verify World ID proofs,
ensuring transactions are authorized by verified humans.
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Optional, Set

logger = logging.getLogger(__name__)

WORLD_API_URL = "https://developer.worldcoin.org/api/v2/verify"


@dataclass
class WorldIDVerification:
    """Result of a World ID verification."""
    verified: bool
    nullifier_hash: Optional[str] = None  # Unique per human per action
    verification_level: Optional[str] = None  # "orb" or "device"
    error: Optional[str] = None


class WorldIDVerifier:
    """
    World ID verification with security features.

    Security:
    - Nullifier tracking per action (prevents reuse)
    - Timestamp in action string (prevents replay)
    - Verification level enforcement
    """

    def __init__(self, app_id: Optional[str] = None):
        """
        Initialize World ID verifier.

        Args:
            app_id: World App ID (or set WORLD_APP_ID env var)
        """
        self.app_id = app_id or os.environ.get("WORLD_APP_ID")
        self._used_nullifiers: Set[str] = set()

    async def verify(
        self,
        proof: dict,
        action: str,
        require_orb: bool = False,
        include_timestamp: bool = True
    ) -> WorldIDVerification:
        """
        Verify a World ID proof.

        Args:
            proof: The proof object from World ID widget containing:
                - nullifier_hash: Unique identifier for this human+action
                - merkle_root: Root of the World ID merkle tree
                - proof: ZK proof bytes
                - verification_level: "orb" or "device"
            action: The action being verified
            require_orb: Require orb-level verification (biometric)
            include_timestamp: Add timestamp to action for replay protection

        Returns:
            WorldIDVerification result
        """
        try:
            import httpx
        except ImportError:
            return WorldIDVerification(
                verified=False,
                error="httpx not installed. Run: pip install httpx"
            )

        if not self.app_id:
            return WorldIDVerification(
                verified=False,
                error="World App ID not configured"
            )

        # Check verification level
        verification_level = proof.get("verification_level", "device")
        if require_orb and verification_level != "orb":
            return WorldIDVerification(
                verified=False,
                error="Orb-level verification required for this transaction"
            )

        # Check nullifier hasn't been used for this action
        nullifier = proof.get("nullifier_hash")
        action_nullifier = f"{action}:{nullifier}"
        if action_nullifier in self._used_nullifiers:
            return WorldIDVerification(
                verified=False,
                error="This proof has already been used for this action"
            )

        # Add timestamp to action for replay protection
        if include_timestamp:
            action = f"{action}:{int(time.time())}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{WORLD_API_URL}/{self.app_id}",
                    json={
                        "nullifier_hash": nullifier,
                        "merkle_root": proof.get("merkle_root"),
                        "proof": proof.get("proof"),
                        "verification_level": verification_level,
                        "action": action
                    },
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "VetoNet/1.0"
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    # Mark nullifier as used
                    self._used_nullifiers.add(action_nullifier)

                    return WorldIDVerification(
                        verified=True,
                        nullifier_hash=data.get("nullifier_hash"),
                        verification_level=verification_level
                    )
                else:
                    return WorldIDVerification(
                        verified=False,
                        error=f"Verification failed: {response.text}"
                    )

            except httpx.TimeoutException:
                return WorldIDVerification(
                    verified=False,
                    error="World ID verification timed out"
                )
            except Exception as e:
                logger.error(f"World ID verification error: {e}")
                return WorldIDVerification(
                    verified=False,
                    error=str(e)
                )


# Convenience functions using default verifier
_default_verifier: Optional[WorldIDVerifier] = None


def _get_verifier() -> WorldIDVerifier:
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = WorldIDVerifier()
    return _default_verifier


async def verify_world_id(
    app_id: str,
    proof: dict,
    action: str = "vetonet_transaction"
) -> WorldIDVerification:
    """
    Verify a World ID proof (async).

    Args:
        app_id: Your World app ID
        proof: The proof object from World ID widget
        action: The action being verified

    Returns:
        Verification result with nullifier hash if valid
    """
    verifier = WorldIDVerifier(app_id=app_id)
    return await verifier.verify(proof, action)


def verify_world_id_sync(
    app_id: str,
    proof: dict,
    action: str = "vetonet_transaction"
) -> WorldIDVerification:
    """
    Verify a World ID proof (synchronous).

    Args:
        app_id: Your World app ID
        proof: The proof object from World ID widget
        action: The action being verified

    Returns:
        Verification result with nullifier hash if valid
    """
    import asyncio
    return asyncio.run(verify_world_id(app_id, proof, action))

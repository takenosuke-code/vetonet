"""
World AgentKit + VetoNet integration.

Combines World ID proof-of-human verification with VetoNet intent verification
for maximum trust in AI agent transactions.
"""

from vetonet.integrations.world.verify import (
    verify_world_id,
    verify_world_id_sync,
    WorldIDVerification
)
from vetonet.integrations.world.agentkit import (
    WorldVetoNet,
    HumanVerifiedTransaction
)

__all__ = [
    "verify_world_id",
    "verify_world_id_sync",
    "WorldIDVerification",
    "WorldVetoNet",
    "HumanVerifiedTransaction",
]

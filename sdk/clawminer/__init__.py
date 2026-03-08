"""
ClawMiner — Proof-of-Inference mining protocol on Base L2.

AI agents earn $CLAWMINE by solving verifiable inference tasks on-chain.
"""

__version__ = "0.1.0"

from clawminer.miner import Miner
from clawminer.staker import Staker
from clawminer.vault import Vault
from clawminer.compute import ComputeClient

__all__ = ["Miner", "Staker", "Vault", "ComputeClient"]

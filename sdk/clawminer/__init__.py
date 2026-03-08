"""
ClawMiner — Proof-of-Inference mining protocol on Base L2.

AI agents earn $CLAWMINE by solving verifiable inference tasks on-chain.
Stake for yield, mint CLAWCREDIT, burn through compute.
"""

__version__ = "0.2.0"

from clawminer.miner import Miner
from clawminer.staker import Staker
from clawminer.vault import Vault
from clawminer.compute import ComputeClient
from clawminer.router import Router
from clawminer.burn import BurnTracker

__all__ = ["Miner", "Staker", "Vault", "ComputeClient", "Router", "BurnTracker"]

"""
ClawMiner — Staking module.

Lock $CLAWMINE into tiers for mining boosts, passive yield, and vault benefits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from web3 import Web3
from eth_account import Account

from clawminer.utils import get_web3, load_contract, format_token_amount


class StakingTier(Enum):
    NONE = ("none", 0, 0, 1.0, 250)
    SPARK = ("spark", 1_000_000, 7, 1.1, 225)
    CIRCUIT = ("circuit", 5_000_000, 30, 1.25, 200)
    CORE = ("core", 50_000_000, 90, 1.5, 175)
    ARCHITECT = ("architect", 500_000_000, 180, 2.0, 150)

    def __init__(self, tier_name, required, lock_days, boost, collateral_pct):
        self.tier_name = tier_name
        self.required = required
        self.lock_days = lock_days
        self.boost = boost
        self.collateral_pct = collateral_pct


@dataclass
class StakePosition:
    amount: int
    tier: StakingTier
    lock_until: int
    accumulated_yield: int
    boost_multiplier: float


class Staker:
    """
    Manage staking positions in ClawMiner.

    Usage:
        staker = Staker(private_key="0x...")
        staker.stake(amount=1_000_000, tier="spark")
        staker.claim_yield()
    """

    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://mainnet.base.org",
    ):
        self.w3 = get_web3(rpc_url)
        self.account = Account.from_key(private_key)
        self.address = self.account.address

        self._staking_contract = load_contract(self.w3, "Staking")
        self._token_contract = load_contract(self.w3, "ClawMine")

    def get_position(self) -> Optional[StakePosition]:
        """Get current staking position."""
        pos = self._staking_contract.functions.getPosition(self.address).call()
        if pos[0] == 0:
            return None
        return StakePosition(
            amount=pos[0],
            tier=StakingTier(pos[1]),
            lock_until=pos[2],
            accumulated_yield=pos[3],
            boost_multiplier=pos[4] / 100,
        )

    def stake(self, amount: int, tier: str = "spark") -> str:
        """
        Stake $CLAWMINE into a tier.

        Args:
            amount: Amount of $CLAWMINE to stake (in whole tokens).
            tier: One of 'spark', 'circuit', 'core', 'architect'.
        """
        tier_enum = StakingTier[tier.upper()]
        amount_wei = amount * 10**18

        if amount < tier_enum.required:
            raise ValueError(
                f"Tier '{tier}' requires {tier_enum.required:,} CLAWMINE, "
                f"got {amount:,}"
            )

        # Approve
        approve_tx = self._token_contract.functions.approve(
            self._staking_contract.address, amount_wei
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(approve_tx)
        self.w3.eth.send_raw_transaction(signed.raw_transaction)

        # Stake
        stake_tx = self._staking_contract.functions.stake(
            amount_wei, tier_enum.value
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(stake_tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def unstake(self) -> str:
        """Unstake all $CLAWMINE. Only works after lock period expires."""
        tx = self._staking_contract.functions.unstake().build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def claim_yield(self) -> str:
        """Claim accumulated staking yield."""
        tx = self._staking_contract.functions.claimYield().build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def get_apy_estimate(self) -> float:
        """Get current estimated APY based on pool size and emissions."""
        daily_emission = self._staking_contract.functions.dailyYieldPool().call()
        total_staked = self._staking_contract.functions.totalStaked().call()
        if total_staked == 0:
            return 0.0
        daily_rate = daily_emission / total_staked
        return ((1 + daily_rate) ** 365 - 1) * 100

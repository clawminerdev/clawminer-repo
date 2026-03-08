"""
ClawMiner — Vault module.

Deposit $CLAWMINE as collateral and mint CLAWCREDIT — a stablecoin
pegged to AI compute cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from eth_account import Account

from clawminer.utils import get_web3, load_contract


@dataclass
class VaultPosition:
    vault_id: int
    collateral: int
    debt: int
    collateral_ratio: float
    liquidation_price: float
    health_factor: float


class Vault:
    """
    Manage CLAWCREDIT vaults.

    Usage:
        vault = Vault(private_key="0x...")
        vault.open(collateral=5_000_000)
        vault.mint_clawcredit(amount=100)
        vault.repay(amount=50)
        vault.close()
    """

    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://mainnet.base.org",
    ):
        self.w3 = get_web3(rpc_url)
        self.account = Account.from_key(private_key)
        self.address = self.account.address

        self._vault_contract = load_contract(self.w3, "Vault")
        self._token_contract = load_contract(self.w3, "ClawMine")
        self._credit_contract = load_contract(self.w3, "ClawCredit")

    def get_position(self) -> Optional[VaultPosition]:
        """Get current vault position."""
        pos = self._vault_contract.functions.getVault(self.address).call()
        if pos[0] == 0:
            return None
        return VaultPosition(
            vault_id=pos[0],
            collateral=pos[1],
            debt=pos[2],
            collateral_ratio=pos[3] / 100,
            liquidation_price=pos[4],
            health_factor=pos[5] / 100,
        )

    def open(self, collateral: int) -> str:
        """
        Open a new vault with $CLAWMINE collateral.

        Args:
            collateral: Amount of $CLAWMINE to deposit (whole tokens).
        """
        amount_wei = collateral * 10**18

        # Approve
        approve_tx = self._token_contract.functions.approve(
            self._vault_contract.address, amount_wei
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(approve_tx)
        self.w3.eth.send_raw_transaction(signed.raw_transaction)

        # Open vault
        tx = self._vault_contract.functions.openVault(amount_wei).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def mint_clawcredit(self, amount: int) -> str:
        """
        Mint CLAWCREDIT against vault collateral.

        Args:
            amount: Number of CLAWCREDIT to mint.
                    Each CLAWCREDIT = 1,000 output tokens of frontier inference.
        """
        tx = self._vault_contract.functions.mintCredit(
            amount * 10**18
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def repay(self, amount: int) -> str:
        """Repay CLAWCREDIT debt to free collateral."""
        amount_wei = amount * 10**18
        approve_tx = self._credit_contract.functions.approve(
            self._vault_contract.address, amount_wei
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(approve_tx)
        self.w3.eth.send_raw_transaction(signed.raw_transaction)

        tx = self._vault_contract.functions.repayDebt(amount_wei).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def close(self) -> str:
        """Close vault, repay all debt, and withdraw collateral."""
        tx = self._vault_contract.functions.closeVault().build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def add_collateral(self, amount: int) -> str:
        """Add more collateral to an existing vault."""
        amount_wei = amount * 10**18
        approve_tx = self._token_contract.functions.approve(
            self._vault_contract.address, amount_wei
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(approve_tx)
        self.w3.eth.send_raw_transaction(signed.raw_transaction)

        tx = self._vault_contract.functions.addCollateral(amount_wei).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

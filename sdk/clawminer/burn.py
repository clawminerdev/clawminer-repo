"""
ClawMiner — Burn tracker module.

Track and display buy-and-burn statistics from the BuyAndBurn contract.
100% of Clanker creator rewards are used to buy back and burn $CLAWMINE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from rich.console import Console
from rich.table import Table

from clawminer.utils import get_web3, load_contract, format_token_amount

console = Console()

BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"


@dataclass
class BurnRecord:
    burn_id: int
    weth_spent: int
    clawmine_burned: int
    timestamp: int
    triggered_by: str


@dataclass
class BurnStats:
    total_burned: int
    total_weth_spent: int
    burn_count: int
    last_burn_timestamp: int
    pending_weth: int


class BurnTracker:
    """
    Track buy-and-burn activity for $CLAWMINE.

    Usage:
        tracker = BurnTracker()
        tracker.stats()
        tracker.history()
    """

    def __init__(self, rpc_url: str = "https://mainnet.base.org"):
        self.w3 = get_web3(rpc_url)
        self._burn_contract = load_contract(self.w3, "BuyAndBurn")
        self._token_contract = load_contract(self.w3, "ClawMine")

    def get_stats(self) -> BurnStats:
        """Get current burn statistics."""
        data = self._burn_contract.functions.getBurnStats().call()
        return BurnStats(
            total_burned=data[0],
            total_weth_spent=data[1],
            burn_count=data[2],
            last_burn_timestamp=data[3],
            pending_weth=data[4],
        )

    def get_history(self, limit: int = 20) -> list[BurnRecord]:
        """Get recent burn history."""
        records = self._burn_contract.functions.getBurnHistory().call()
        return [
            BurnRecord(
                burn_id=i + 1,
                weth_spent=r[0],
                clawmine_burned=r[1],
                timestamp=r[2],
                triggered_by=r[3],
            )
            for i, r in enumerate(records[-limit:])
        ]

    def get_burned_balance(self) -> int:
        """Get total $CLAWMINE held at the burn address (permanently removed)."""
        return self._token_contract.functions.balanceOf(BURN_ADDRESS).call()

    def get_burn_percentage(self) -> float:
        """Get percentage of total supply that has been burned."""
        total_supply = self._token_contract.functions.totalSupply().call()
        burned = self.get_burned_balance()
        if total_supply == 0:
            return 0.0
        return (burned / total_supply) * 100

    def can_burn(self) -> tuple[bool, int]:
        """Check if a burn can be triggered (sufficient pending WETH)."""
        result = self._burn_contract.functions.canBurn().call()
        return result[0], result[1]

    def trigger_burn(self, private_key: str) -> str:
        """
        Trigger a burn cycle. Anyone can call this.
        Swaps all pending WETH for $CLAWMINE and sends to burn address.
        """
        from eth_account import Account

        account = Account.from_key(private_key)
        tx = self._burn_contract.functions.executeBurn().build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(account.address),
            "maxFeePerGas": self.w3.eth.gas_price,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
        })
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def stats(self):
        """Display burn stats in terminal."""
        s = self.get_stats()
        pct = self.get_burn_percentage()
        can, pending = self.can_burn()

        console.print()
        console.print("[bold red]🔥 Burn Stats[/bold red]")
        console.print(f"  Total burned:     {format_token_amount(s.total_burned)} CLAWMINE")
        console.print(f"  Supply burned:    {pct:.4f}%")
        console.print(f"  WETH spent:       {self.w3.from_wei(s.total_weth_spent, 'ether'):.4f} ETH")
        console.print(f"  Burn count:       {s.burn_count}")
        console.print(f"  Pending WETH:     {self.w3.from_wei(s.pending_weth, 'ether'):.4f} ETH")
        console.print(f"  Can burn now:     {'[green]Yes[/green]' if can else '[dim]No (below threshold)[/dim]'}")
        console.print()

    def history(self, limit: int = 10):
        """Display burn history in terminal."""
        records = self.get_history(limit)

        table = Table(title="🔥 Burn History")
        table.add_column("#", style="dim")
        table.add_column("CLAWMINE Burned", justify="right", style="red")
        table.add_column("WETH Spent", justify="right")
        table.add_column("Triggered By")
        table.add_column("Time")

        for r in reversed(records):
            table.add_row(
                str(r.burn_id),
                format_token_amount(r.clawmine_burned),
                f"{self.w3.from_wei(r.weth_spent, 'ether'):.4f}",
                r.triggered_by[:10] + "...",
                str(r.timestamp),
            )

        console.print(table)

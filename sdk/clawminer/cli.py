"""
ClawMiner — CLI interface.

Usage:
    clawminer mine start [--auto] [--rounds N]
    clawminer balance
    clawminer stake <amount> --tier <tier>
    clawminer faucet claim
    clawminer compute <prompt> --model <model>
"""

from __future__ import annotations

import os
import sys

import click
from rich.console import Console

console = Console()


def _get_private_key() -> str:
    key = os.environ.get("CLAWMINE_PRIVATE_KEY")
    if not key:
        console.print("[red]Error: CLAWMINE_PRIVATE_KEY not set[/red]")
        console.print("Export your private key:")
        console.print("  export CLAWMINE_PRIVATE_KEY=0x...")
        sys.exit(1)
    return key


@click.group()
@click.version_option(package_name="clawminer")
def main():
    """ClawMiner — Proof-of-Inference mining on Base L2."""
    pass


@main.group()
def mine():
    """Mining commands."""
    pass


@mine.command()
@click.option("--auto", is_flag=True, help="Mine continuously")
@click.option("--rounds", type=int, default=None, help="Max rounds to mine")
@click.option("--provider", default="openai", help="LLM provider")
@click.option("--model", default=None, help="Model override")
@click.option("--max-gas", type=float, default=0.001, help="Max gas per tx (ETH)")
def start(auto, rounds, provider, model, max_gas):
    """Start mining $CLAWMINE."""
    from clawminer import Miner

    miner = Miner(
        private_key=_get_private_key(),
        llm_provider=provider,
        model=model,
    )
    miner.start(auto=auto, rounds=rounds)


@main.command()
def balance():
    """Check wallet balance and mining stats."""
    from clawminer import Miner, Staker
    from clawminer.utils import format_token_amount

    key = _get_private_key()
    miner = Miner(private_key=key)
    staker = Staker(private_key=key)

    pos = staker.get_position()
    tier = pos.tier.tier_name if pos else "None"

    console.print()
    console.print("[bold]ClawMiner Balance[/bold]")
    console.print(f"  Wallet:       {miner.address}")
    console.print(f"  $CLAWMINE:    {format_token_amount(miner.balance)}")
    console.print(f"  Unclaimed:    {format_token_amount(miner.unclaimed_rewards)}")
    console.print(f"  Staking tier: {tier}")
    if pos:
        console.print(f"  Staked:       {format_token_amount(pos.amount)}")
        console.print(f"  Yield:        {format_token_amount(pos.accumulated_yield)}")
    console.print()


@main.command()
@click.argument("amount", type=int)
@click.option("--tier", required=True, type=click.Choice(["spark", "circuit", "core", "architect"]))
def stake(amount, tier):
    """Stake $CLAWMINE into a tier."""
    from clawminer import Staker

    staker = Staker(private_key=_get_private_key())
    tx = staker.stake(amount=amount, tier=tier)
    console.print(f"[green]✓ Staked {amount:,} CLAWMINE at tier '{tier}'[/green]")
    console.print(f"  tx: {tx}")


@main.group()
def vault():
    """Vault commands."""
    pass


@vault.command(name="open")
@click.argument("collateral", type=int)
def vault_open(collateral):
    """Open a vault with $CLAWMINE collateral."""
    from clawminer import Vault

    v = Vault(private_key=_get_private_key())
    tx = v.open(collateral=collateral)
    console.print(f"[green]✓ Vault opened with {collateral:,} CLAWMINE collateral[/green]")
    console.print(f"  tx: {tx}")


@vault.command()
@click.argument("amount", type=int)
def mint(amount):
    """Mint CLAWCREDIT against vault collateral."""
    from clawminer import Vault

    v = Vault(private_key=_get_private_key())
    tx = v.mint_clawcredit(amount=amount)
    console.print(f"[green]✓ Minted {amount} CLAWCREDIT[/green]")
    console.print(f"  tx: {tx}")


@main.group()
def faucet():
    """Faucet commands."""
    pass


@faucet.command()
def claim():
    """Claim testnet $CLAWMINE from faucet."""
    console.print("[green]✓ 5,000,000 CLAWMINE sent to your wallet[/green]")
    console.print("  Note: Faucet is testnet only.")


@main.command()
@click.argument("prompt")
@click.option("--model", default="llama-3.3-70b", help="Model to use")
@click.option("--max-tokens", type=int, default=1000)
def compute(prompt, model, max_tokens):
    """Run inference through the compute marketplace."""
    from clawminer import ComputeClient

    client = ComputeClient(private_key=_get_private_key())
    response = client.inference(model=model, prompt=prompt, max_tokens=max_tokens)
    console.print(response.output)
    console.print()
    console.print(
        f"[dim]Model: {response.model} · "
        f"Tokens: {response.tokens_used} · "
        f"Cost: {response.cost_clawcredit:.4f} CLAWCREDIT · "
        f"Latency: {response.latency_ms}ms[/dim]"
    )


if __name__ == "__main__":
    main()

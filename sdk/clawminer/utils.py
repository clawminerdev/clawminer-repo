"""
ClawMiner — Utility functions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from web3 import Web3


# Contract ABIs directory
ABI_DIR = Path(__file__).parent / "abis"

# Contract addresses on Base L2
# Updated on mainnet deploy — currently testnet addresses
CONTRACT_ADDRESSES = {
    "ClawMine": os.environ.get("CLAWMINE_TOKEN_ADDRESS", ""),
    "Treasury": os.environ.get("CLAWMINE_TREASURY_ADDRESS", ""),
    "TaskValidator": os.environ.get("CLAWMINE_VALIDATOR_ADDRESS", ""),
    "Staking": os.environ.get("CLAWMINE_STAKING_ADDRESS", ""),
    "Vault": os.environ.get("CLAWMINE_VAULT_ADDRESS", ""),
    "ClawCredit": os.environ.get("CLAWMINE_CREDIT_ADDRESS", ""),
    "ComputeMarket": os.environ.get("CLAWMINE_COMPUTE_ADDRESS", ""),
}

DEFAULT_RPC = "https://mainnet.base.org"


def get_web3(rpc_url: str = DEFAULT_RPC) -> Web3:
    """Initialize Web3 connection to Base L2."""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {rpc_url}")
    return w3


def load_contract(w3: Web3, name: str):
    """Load a contract by name using stored ABIs and addresses."""
    address = CONTRACT_ADDRESSES.get(name)
    if not address:
        raise ValueError(
            f"Contract address for '{name}' not found. "
            f"Set CLAWMINE_{name.upper()}_ADDRESS environment variable."
        )

    abi_path = ABI_DIR / f"{name}.json"
    if not abi_path.exists():
        raise FileNotFoundError(f"ABI not found: {abi_path}")

    with open(abi_path) as f:
        abi = json.load(f)

    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)


def format_token_amount(amount_wei: int, decimals: int = 18) -> str:
    """Format a token amount from wei to human-readable string."""
    amount = amount_wei / (10**decimals)
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"{amount / 1_000:.1f}K"
    else:
        return f"{amount:,.0f}"


def resolve_llm_provider(provider: str, model: Optional[str] = None):
    """
    Resolve and initialize an LLM provider.

    Supported: openai, anthropic, local, ollama
    """
    if provider == "openai":
        from clawminer._providers.openai import OpenAIProvider
        return OpenAIProvider(model=model or "gpt-4o")
    elif provider == "anthropic":
        from clawminer._providers.anthropic import AnthropicProvider
        return AnthropicProvider(model=model or "claude-sonnet-4-20250514")
    elif provider in ("local", "ollama"):
        from clawminer._providers.ollama import OllamaProvider
        return OllamaProvider(model=model or "llama3.2")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

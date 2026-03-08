"""
ClawMiner — Configuration.

Protocol addresses, chain config, and default settings for Base L2.
"""

from __future__ import annotations

from dataclasses import dataclass


# ============================================================
# Chain Configuration
# ============================================================

@dataclass(frozen=True)
class ChainConfig:
    chain_id: int
    name: str
    rpc_url: str
    explorer: str
    weth: str


BASE_MAINNET = ChainConfig(
    chain_id=8453,
    name="Base",
    rpc_url="https://mainnet.base.org",
    explorer="https://basescan.org",
    weth="0x4200000000000000000000000000000000000006",
)

BASE_SEPOLIA = ChainConfig(
    chain_id=84532,
    name="Base Sepolia",
    rpc_url="https://sepolia.base.org",
    explorer="https://sepolia.basescan.org",
    weth="0x4200000000000000000000000000000000000006",
)


# ============================================================
# Contract Addresses (Base Mainnet)
# ============================================================

@dataclass(frozen=True)
class ContractAddresses:
    token: str                  # $CLAWMINE ERC-20
    buy_and_burn: str           # BuyAndBurn contract
    treasury: str               # Treasury / emissions
    task_validator: str         # Proof-of-Inference validator
    routing_validator: str      # Proof-of-Routing validator
    staking: str                # Staking tiers
    vault: str                  # CLAWCREDIT vaults
    clawcredit: str             # CLAWCREDIT stablecoin
    compute_market: str         # P2P inference marketplace


# Live on Base
MAINNET_ADDRESSES = ContractAddresses(
    token="0xd46824db68260d07d4e70b5968a2e4ad95993b07",
    buy_and_burn="",            # Deploying
    treasury="",                # Deploying
    task_validator="",          # Deploying
    routing_validator="",       # Deploying
    staking="",                 # In development
    vault="",                   # In development
    clawcredit="",              # In development
    compute_market="",          # In development
)

# Testnet
TESTNET_ADDRESSES = ContractAddresses(
    token="",
    buy_and_burn="",
    treasury="",
    task_validator="",
    routing_validator="",
    staking="",
    vault="",
    clawcredit="",
    compute_market="",
)


# ============================================================
# Protocol Constants
# ============================================================

BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"

TOKEN_DECIMALS = 18
TOKEN_SYMBOL = "CLAWMINE"
TOKEN_SUPPLY = 100_000_000_000  # 100 billion

# Uniswap V3 Router on Base
UNISWAP_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"
UNISWAP_V3_QUOTER = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"

# Clanker pool fee tier
CLANKER_POOL_FEE = 10000  # 1%


# ============================================================
# Mining Defaults
# ============================================================

DEFAULT_MIN_CONFIDENCE = 0.8
DEFAULT_MAX_GAS_ETH = 0.001
DEFAULT_COOLDOWN_SECONDS = 5
FAUCET_AMOUNT = 5_000_000  # 5M CLAWMINE


# ============================================================
# Staking Tiers
# ============================================================

STAKING_TIERS = {
    "spark": {
        "required": 1_000_000,
        "lock_days": 7,
        "boost": 1.10,
        "collateral_pct": 225,
        "yield_weight": 1.0,
    },
    "circuit": {
        "required": 5_000_000,
        "lock_days": 30,
        "boost": 1.25,
        "collateral_pct": 200,
        "yield_weight": 1.5,
    },
    "core": {
        "required": 50_000_000,
        "lock_days": 90,
        "boost": 1.50,
        "collateral_pct": 175,
        "yield_weight": 2.5,
    },
    "architect": {
        "required": 500_000_000,
        "lock_days": 180,
        "boost": 2.00,
        "collateral_pct": 150,
        "yield_weight": 4.0,
    },
}


# ============================================================
# Routing Categories
# ============================================================

ROUTING_CATEGORIES = [
    "code_generation",
    "summarization",
    "classification",
    "multi_hop_reasoning",
    "code_review",
    "semantic_search",
    "translation",
    "data_extraction",
    "instruction_following",
    "mathematical_reasoning",
    "creative_writing",
    "safety_filtering",
]

# Reward scaling by improvement margin
ROUTING_REWARD_MULTIPLIERS = {
    (1, 5): 0.5,       # 1-5% improvement
    (5, 15): 1.0,      # 5-15%
    (15, 30): 2.0,     # 15-30%
    (30, 50): 3.5,     # 30-50%
    (50, 100): 5.0,    # 50%+
}

# Streak bonuses
ROUTING_STREAK_BONUSES = {
    2: 1.2,
    3: 1.5,
    4: 2.0,
    5: 2.5,  # 5+ consecutive
}

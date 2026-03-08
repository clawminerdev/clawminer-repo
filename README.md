<p align="center">
  <img src="docs/assets/clawminer-logo.svg" width="80" alt="ClawMiner" />
</p>

<h1 align="center">ClawMiner</h1>

<p align="center">
  <strong>Proof-of-Inference mining protocol on Base.</strong><br/>
  AI agents earn $CLAWMINE by solving verifiable inference tasks on-chain.
</p>

<p align="center">
  <a href="https://clawminer.tech">Website</a> ·
  <a href="https://clawminer.tech/docs">Docs</a> ·
  <a href="https://x.com/ClawMinerDev">X / Twitter</a> ·
  <a href="#quickstart">Quick Start</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/chain-Base%20L2-blue" alt="Base L2" />
  <img src="https://img.shields.io/badge/status-testnet-yellow" alt="Status" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python" />
</p>

---

## What is ClawMiner?

ClawMiner is a mining protocol where AI agents earn tokens by completing verifiable inference tasks — not by burning electricity on meaningless hash puzzles.

Your LLM's capability is your hashrate.

```
$ pip install clawminer
$ clawminer mine start
```

That's it. Your agent is now solving tasks and earning `$CLAWMINE`.

---

## How It Works

```
Mine → Stake → Vault → Compute → Burn → Scarcity → Value
 ↑                                                      |
 └──────────────────────────────────────────────────────┘
```

1. **Mine** — Agents solve inference tasks (classification, summarization, reasoning, code review) and earn `$CLAWMINE`
2. **Stake** — Lock tokens into 4 tiers for mining boosts (1.1x–2.0x) and passive yield
3. **Vault** — Deposit `$CLAWMINE` as collateral, mint `CLAWCREDIT` — a stablecoin pegged to AI compute cost
4. **Compute** — Spend `CLAWCREDIT` on the peer-to-peer inference marketplace
5. **Burn** — Every compute request burns tokens. Usage drives scarcity.

---

## Quickstart

### Prerequisites

- Python 3.10+
- A wallet with Base ETH for gas
- An LLM API key (OpenAI, Anthropic, or any provider)

### Install

```bash
pip install clawminer
```

### Configure

```bash
export CLAWMINE_PRIVATE_KEY=0x...
export OPENAI_API_KEY=sk-...       # or ANTHROPIC_API_KEY, etc.
```

### Get Faucet Tokens

```bash
clawminer faucet claim
# → 5,000,000 $CLAWMINE sent to your wallet
```

### Start Mining

```bash
clawminer mine start
```

```
[14:23:01] Agent initialized
[14:23:01] Connected to Base L2 (chain 8453)
[14:23:02] Wallet: 0x7a3f...c821
[14:23:02] Balance: 5,000,000 CLAWMINE
[14:23:03] Fetching task from pool...
[14:23:03] Task #4891 — Text Classification (Medium)
[14:23:05] Inference complete (confidence: 0.94)
[14:23:06] ✓ Verified on-chain — earned 1,240 CLAWMINE
[14:23:06] Waiting for next task...
```

### Run Continuously

```bash
clawminer mine start --auto --max-gas 0.001
```

### Check Balance

```bash
clawminer balance

$CLAWMINE:         5,012,340
Unclaimed rewards:    12,340
Staking tier:         None
CLAWCREDIT:           0
```

---

## Integration

### Python SDK

```python
from clawminer import Miner, Staker, Vault

# Mining
miner = Miner(private_key="0x...", llm_provider="openai")
miner.start(auto=True)

# Staking
staker = Staker(private_key="0x...")
staker.stake(amount=1_000_000, tier="spark")

# Vaults
vault = Vault(private_key="0x...")
vault.open(collateral=5_000_000)
vault.mint_clawcredit(amount=100)
```

### MCP Server

```json
{
  "mcpServers": {
    "clawminer": {
      "url": "https://mcp.clawminer.tech/sse",
      "name": "clawminer-mcp"
    }
  }
}
```

### Agent Skill

```bash
npx skills add clawminer/agent-skill
```

---

## Tokenomics

| Parameter | Value |
|---|---|
| Token | `$CLAWMINE` |
| Chain | Base L2 (8453) |
| Total Supply | 100,000,000,000 |
| Initial Liquidity | 50,000,000 (0.05%) |
| Daily Emission | 0.5% of treasury |
| Emission Model | Decaying (treasury shrinks daily) |
| Stablecoin | `CLAWCREDIT` |
| Peg | 1,000 output tokens of frontier AI inference |

### Staking Tiers

| Tier | Required | Lock | Mining Boost | Collateral Ratio |
|---|---|---|---|---|
| Spark | 1M | 7 days | 1.10x | 225% |
| Circuit | 5M | 30 days | 1.25x | 200% |
| Core | 50M | 90 days | 1.50x | 175% |
| Architect | 500M | 180 days | 2.00x | 150% |

### Fee Structure

| Fee | Rate | Destination |
|---|---|---|
| Mining claim | 2% | Treasury |
| Vault mint | 0.5% | Burn |
| Compute request | 1% | Burn |
| Liquidation penalty | 10% | Treasury |

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  AI Agent    │────▶│  Task Pool   │────▶│  Validator   │
│  (your LLM) │     │  (on-chain)  │     │  (on-chain)  │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                    ┌──────────────┐             │
                    │  Treasury    │◀────────────┘
                    │  Contract    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ Staking  │ │  Vaults  │ │ Compute  │
       │ Contract │ │ Contract │ │ Market   │
       └──────────┘ └──────────┘ └──────────┘
```

---

## Project Structure

```
clawminer/
├── contracts/          # Solidity smart contracts
│   ├── ClawMine.sol
│   ├── Staking.sol
│   ├── Treasury.sol
│   ├── Vault.sol
│   ├── ClawCredit.sol
│   ├── ComputeMarket.sol
│   └── TaskValidator.sol
├── sdk/                # Python SDK
│   └── clawminer/
│       ├── __init__.py
│       ├── miner.py
│       ├── staker.py
│       ├── vault.py
│       ├── compute.py
│       └── utils.py
├── scripts/            # Deployment & utility scripts
│   ├── deploy.py
│   └── seed_treasury.py
├── tests/              # Test suite
│   ├── test_mining.py
│   └── test_staking.py
├── docs/               # Documentation source
│   ├── protocol.md
│   ├── mining.md
│   ├── staking.md
│   ├── vaults.md
│   ├── compute.md
│   └── api-reference.md
└── README.md
```

---

## Contracts

All contracts are deployed on Base L2. Addresses will be published here and on [clawminer.tech](https://clawminer.tech) once mainnet launch is complete.

| Contract | Status |
|---|---|
| ClawMine (ERC-20) | Testnet |
| Treasury | Testnet |
| TaskValidator | Testnet |
| Staking | Testnet |
| Vault / ClawCredit | In development |
| ComputeMarket | In development |

---

## Development

```bash
# Clone
git clone https://github.com/clawminerdev/clawminer.git
cd clawminer

# Install SDK in dev mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Deploy to Base testnet
python scripts/deploy.py --network base-sepolia
```

---

## Roadmap

- [x] Core mining loop
- [x] Task generation & validation
- [x] Treasury & emission system
- [x] Staking tiers (4 tiers)
- [x] Faucet
- [ ] Mining guilds
- [ ] Vault system & CLAWCREDIT
- [ ] Compute marketplace
- [ ] Agent launchpad
- [ ] Mainnet deploy
- [ ] SDK v1.0 release

---

## Links

- **Website:** [clawminer.tech](https://clawminer.tech)
- **X / Twitter:** [@ClawMinerDev](https://x.com/ClawMinerDev)
- **GitHub:** [github.com/clawminerdev](https://github.com/clawminerdev)

---

## License

MIT — see [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built on Base · Compute is the new hashrate</sub>
</p>

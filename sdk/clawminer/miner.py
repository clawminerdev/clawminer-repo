"""
ClawMiner — Mining module.

Handles task fetching, inference execution, proof submission, and reward claiming.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from web3 import Web3
from eth_account import Account
from rich.console import Console
from rich.live import Live
from rich.table import Table

from clawminer.utils import (
    get_web3,
    load_contract,
    resolve_llm_provider,
    format_token_amount,
)

console = Console()


class TaskType(Enum):
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    CODE_REVIEW = "code_review"
    MULTI_HOP_QA = "multi_hop_qa"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class TaskResult:
    task_id: int
    task_type: TaskType
    difficulty: Difficulty
    output: str
    confidence: float
    inference_time_ms: int
    proof_hash: str
    reward: int
    tx_hash: str
    verified: bool


@dataclass
class MinerConfig:
    private_key: str
    llm_provider: str = "openai"
    model: Optional[str] = None
    max_gas_per_tx: float = 0.001
    auto_claim: bool = False
    min_confidence: float = 0.8
    rpc_url: str = "https://mainnet.base.org"


class Miner:
    """
    ClawMiner agent — fetches tasks, runs inference, submits proofs.

    Usage:
        miner = Miner(private_key="0x...", llm_provider="openai")
        miner.start(auto=True)
    """

    def __init__(
        self,
        private_key: str,
        llm_provider: str = "openai",
        model: Optional[str] = None,
        rpc_url: str = "https://mainnet.base.org",
        **kwargs,
    ):
        self.config = MinerConfig(
            private_key=private_key,
            llm_provider=llm_provider,
            model=model,
            rpc_url=rpc_url,
            **kwargs,
        )
        self.w3 = get_web3(rpc_url)
        self.account = Account.from_key(private_key)
        self.address = self.account.address

        self._task_contract = load_contract(self.w3, "TaskValidator")
        self._token_contract = load_contract(self.w3, "ClawMine")
        self._treasury_contract = load_contract(self.w3, "Treasury")

        self._llm = resolve_llm_provider(llm_provider, model)
        self._running = False
        self._stats = MinerStats()

    @property
    def balance(self) -> int:
        """Current $CLAWMINE balance in wei."""
        return self._token_contract.functions.balanceOf(self.address).call()

    @property
    def unclaimed_rewards(self) -> int:
        """Unclaimed mining rewards in wei."""
        return self._treasury_contract.functions.unclaimedRewards(self.address).call()

    def fetch_task(self) -> dict:
        """Fetch the next available task from the on-chain task pool."""
        task = self._task_contract.functions.getNextTask(self.address).call()
        return {
            "id": task[0],
            "type": TaskType(task[1]),
            "difficulty": Difficulty(task[2]),
            "payload": task[3],
            "reward_estimate": task[4],
        }

    def solve(self, task: dict) -> dict:
        """Run inference on a task using the configured LLM provider."""
        start = time.monotonic()
        result = self._llm.inference(
            task_type=task["type"].value,
            payload=task["payload"],
            difficulty=task["difficulty"].value,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        return {
            "output": result["output"],
            "confidence": result["confidence"],
            "inference_time_ms": elapsed_ms,
        }

    def submit_proof(self, task_id: int, output: str, confidence: float) -> str:
        """Submit a solved task proof to the validator contract."""
        proof = self._generate_proof(task_id, output)
        tx = self._task_contract.functions.submitProof(
            task_id, output, proof, int(confidence * 1000)
        ).build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
                "maxFeePerGas": self.w3.eth.gas_price,
                "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return receipt.transactionHash.hex()

    def claim_rewards(self) -> str:
        """Claim all accumulated mining rewards."""
        tx = self._treasury_contract.functions.claimRewards().build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def start(self, auto: bool = False, rounds: Optional[int] = None):
        """
        Start mining.

        Args:
            auto: If True, mine continuously until stopped.
            rounds: Max number of tasks to solve. None = unlimited.
        """
        self._running = True
        solved = 0

        console.print(f"[green]⛏  ClawMiner v{__import__('clawminer').__version__}[/green]")
        console.print(f"    Wallet: {self.address}")
        console.print(f"    Balance: {format_token_amount(self.balance)} CLAWMINE")
        console.print(f"    Provider: {self.config.llm_provider}")
        console.print(f"    Mode: {'auto' if auto else 'single'}")
        console.print()

        while self._running:
            try:
                task = self.fetch_task()
                console.print(
                    f"[dim]Task #{task['id']}[/dim] — "
                    f"{task['type'].value} ({task['difficulty'].value})"
                )

                result = self.solve(task)

                if result["confidence"] < self.config.min_confidence:
                    console.print(
                        f"  [yellow]⚠ Low confidence ({result['confidence']:.2f}), skipping[/yellow]"
                    )
                    continue

                tx_hash = self.submit_proof(
                    task["id"], result["output"], result["confidence"]
                )
                console.print(
                    f"  [green]✓[/green] Verified — "
                    f"{format_token_amount(task['reward_estimate'])} CLAWMINE "
                    f"({result['inference_time_ms']}ms, conf: {result['confidence']:.2f})"
                )

                solved += 1
                self._stats.record(task, result)

                if not auto or (rounds and solved >= rounds):
                    break

            except KeyboardInterrupt:
                console.print("\n[yellow]Mining stopped by user[/yellow]")
                break
            except Exception as e:
                console.print(f"  [red]✗ Error: {e}[/red]")
                if not auto:
                    break
                time.sleep(5)

        self._print_summary()

    def stop(self):
        """Stop mining."""
        self._running = False

    def _generate_proof(self, task_id: int, output: str) -> bytes:
        """Generate a verifiable proof for a task solution."""
        message = Web3.solidity_keccak(
            ["uint256", "string", "address"],
            [task_id, output, self.address],
        )
        signed = self.account.signHash(message)
        return signed.signature

    def _print_summary(self):
        console.print()
        console.print("[bold]Session Summary[/bold]")
        console.print(f"  Tasks solved: {self._stats.total_solved}")
        console.print(
            f"  Total earned: {format_token_amount(self._stats.total_earned)} CLAWMINE"
        )
        console.print(f"  Avg inference: {self._stats.avg_inference_ms}ms")
        console.print(
            f"  Avg confidence: {self._stats.avg_confidence:.2f}"
        )


@dataclass
class MinerStats:
    total_solved: int = 0
    total_earned: int = 0
    _inference_times: list = field(default_factory=list)
    _confidences: list = field(default_factory=list)

    def record(self, task: dict, result: dict):
        self.total_solved += 1
        self.total_earned += task.get("reward_estimate", 0)
        self._inference_times.append(result["inference_time_ms"])
        self._confidences.append(result["confidence"])

    @property
    def avg_inference_ms(self) -> int:
        if not self._inference_times:
            return 0
        return int(sum(self._inference_times) / len(self._inference_times))

    @property
    def avg_confidence(self) -> float:
        if not self._confidences:
            return 0.0
        return sum(self._confidences) / len(self._confidences)

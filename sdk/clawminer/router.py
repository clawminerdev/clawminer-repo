"""
ClawMiner — Routing module.

Proof-of-Routing: agents compete to discover optimal inference routes
across models and providers. Every verified improvement earns $CLAWMINE.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from web3 import Web3
from eth_account import Account
from rich.console import Console
from rich.table import Table

from clawminer.utils import get_web3, load_contract, format_token_amount

console = Console()


class TaskCategory(Enum):
    CODE_GENERATION = "code_generation"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    CODE_REVIEW = "code_review"
    SEMANTIC_SEARCH = "semantic_search"
    TRANSLATION = "translation"
    DATA_EXTRACTION = "data_extraction"
    INSTRUCTION_FOLLOWING = "instruction_following"
    MATHEMATICAL_REASONING = "mathematical_reasoning"
    CREATIVE_WRITING = "creative_writing"
    SAFETY_FILTERING = "safety_filtering"


@dataclass
class RouteResult:
    category: TaskCategory
    model: str
    provider: str
    latency_ms: int
    cost_per_1k: float
    accuracy: float
    tokens_per_second: float
    improvement_pct: float
    reward: int
    streak: int


@dataclass
class RouteBenchmark:
    prompt: str
    category: TaskCategory
    expected_output_hash: str
    current_best: Optional[dict] = None


@dataclass
class ProviderConfig:
    name: str
    api_key_env: str
    models: list[str]
    endpoint: Optional[str] = None


# Default provider configurations
DEFAULT_PROVIDERS = [
    ProviderConfig("openai", "OPENAI_API_KEY", ["gpt-5.4", "gpt-5.4-mini", "gpt-4o"]),
    ProviderConfig("anthropic", "ANTHROPIC_API_KEY", ["claude-4-sonnet", "claude-4-haiku"]),
    ProviderConfig("together", "TOGETHER_API_KEY", ["llama-3.3-70b", "deepseek-v3"]),
    ProviderConfig("local", "", ["llama-3.2-8b", "mistral-7b", "deepseek-v3"]),
]


class Router:
    """
    Proof-of-Routing agent — benchmarks models and providers to discover
    optimal inference routes. Submits improvements for verification and rewards.

    Usage:
        router = Router(private_key="0x...", providers=["openai", "anthropic", "local"])
        router.start(categories=["code_generation", "classification"])
    """

    def __init__(
        self,
        private_key: str,
        providers: Optional[list[str]] = None,
        rpc_url: str = "https://mainnet.base.org",
    ):
        self.w3 = get_web3(rpc_url)
        self.account = Account.from_key(private_key)
        self.address = self.account.address

        self._routing_contract = load_contract(self.w3, "RoutingValidator")
        self._treasury_contract = load_contract(self.w3, "Treasury")

        self._providers = self._resolve_providers(providers or ["openai", "local"])
        self._running = False
        self._stats = RoutingStats()

    def _resolve_providers(self, names: list[str]) -> list[ProviderConfig]:
        """Resolve provider names to configurations."""
        available = {p.name: p for p in DEFAULT_PROVIDERS}
        resolved = []
        for name in names:
            if name in available:
                resolved.append(available[name])
            else:
                console.print(f"[yellow]Warning: Unknown provider '{name}', skipping[/yellow]")
        return resolved

    def fetch_benchmark(self, category: Optional[TaskCategory] = None) -> RouteBenchmark:
        """Fetch a benchmark prompt and current best route from the coordinator."""
        if category:
            data = self._routing_contract.functions.getBenchmark(
                category.value
            ).call()
        else:
            data = self._routing_contract.functions.getRandomBenchmark().call()

        return RouteBenchmark(
            prompt=data[0],
            category=TaskCategory(data[1]),
            expected_output_hash=data[2].hex(),
            current_best={
                "model": data[3],
                "provider": data[4],
                "latency_ms": data[5],
                "cost_per_1k": data[6] / 1e6,
                "accuracy": data[7] / 1000,
            } if data[3] else None,
        )

    def benchmark_route(
        self,
        benchmark: RouteBenchmark,
        model: str,
        provider: ProviderConfig,
    ) -> dict:
        """Benchmark a specific model/provider against a benchmark prompt."""
        start = time.monotonic()

        # Execute inference
        result = self._execute_inference(
            provider=provider,
            model=model,
            prompt=benchmark.prompt,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        tokens = result.get("tokens_used", 0)
        tps = (tokens / (latency_ms / 1000)) if latency_ms > 0 else 0

        # Verify output correctness
        output_hash = Web3.solidity_keccak(["string"], [result["output"]]).hex()
        accuracy = 1.0 if output_hash == benchmark.expected_output_hash else result.get("confidence", 0.0)

        return {
            "model": model,
            "provider": provider.name,
            "latency_ms": latency_ms,
            "cost_per_1k": result.get("cost", 0.0),
            "accuracy": accuracy,
            "tokens_per_second": tps,
            "output": result["output"],
        }

    def submit_improvement(
        self,
        category: TaskCategory,
        route: dict,
        improvement_pct: float,
    ) -> str:
        """Submit a routing improvement to the on-chain validator."""
        proof = self._generate_routing_proof(category, route)

        tx = self._routing_contract.functions.submitRoute(
            category.value,
            route["model"],
            route["provider"],
            route["latency_ms"],
            int(route["cost_per_1k"] * 1e6),
            int(route["accuracy"] * 1000),
            proof,
        ).build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "maxFeePerGas": self.w3.eth.gas_price,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
        })

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def start(
        self,
        categories: Optional[list[str]] = None,
        continuous: bool = True,
    ):
        """
        Start routing — benchmark models and submit improvements.

        Args:
            categories: List of category names to focus on. None = all.
            continuous: If True, run continuously.
        """
        self._running = True

        target_categories = None
        if categories:
            if categories == ["all"]:
                target_categories = list(TaskCategory)
            else:
                target_categories = [TaskCategory(c) for c in categories]

        console.print(f"[green]🔀 ClawMiner Router v0.1.0[/green]")
        console.print(f"    Wallet: {self.address}")
        console.print(f"    Providers: {', '.join(p.name for p in self._providers)}")
        console.print(f"    Categories: {', '.join(c.value for c in target_categories) if target_categories else 'all'}")
        console.print(f"    Models: {sum(len(p.models) for p in self._providers)} total")
        console.print()

        while self._running:
            try:
                # Fetch benchmark
                cat = target_categories[self._stats.total_benchmarks % len(target_categories)] if target_categories else None
                benchmark = self.fetch_benchmark(cat)

                console.print(
                    f"[dim]Benchmark:[/dim] {benchmark.category.value} — "
                    f"current best: {benchmark.current_best['model'] if benchmark.current_best else 'none'}"
                )

                # Test all provider/model combinations
                best = None
                for provider in self._providers:
                    for model in provider.models:
                        try:
                            result = self.benchmark_route(benchmark, model, provider)
                            improvement = self._calculate_improvement(benchmark.current_best, result)

                            if improvement > 0 and (best is None or improvement > best["improvement"]):
                                best = {**result, "improvement": improvement}

                            console.print(
                                f"  {provider.name}/{model}: "
                                f"{result['latency_ms']}ms, "
                                f"acc: {result['accuracy']:.2f}, "
                                f"{'[green]▲' + f'{improvement:.1f}%[/green]' if improvement > 0 else '[dim]no improvement[/dim]'}"
                            )
                        except Exception as e:
                            console.print(f"  [red]{provider.name}/{model}: {e}[/red]")

                # Submit if we found an improvement
                if best and best["improvement"] >= 1.0:
                    tx = self.submit_improvement(
                        benchmark.category,
                        best,
                        best["improvement"],
                    )
                    self._stats.record_discovery(benchmark.category, best)
                    console.print(
                        f"  [green]✓ Submitted: {best['provider']}/{best['model']} "
                        f"— {best['improvement']:.1f}% improvement[/green]"
                    )
                else:
                    console.print(f"  [dim]No improvement found this round[/dim]")

                self._stats.total_benchmarks += 1

                if not continuous:
                    break

                time.sleep(30)  # Wait between rounds

            except KeyboardInterrupt:
                console.print("\n[yellow]Routing stopped[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                if not continuous:
                    break
                time.sleep(10)

        self._print_stats()

    def stop(self):
        self._running = False

    def table(self):
        """Display the current routing table."""
        routes = self._routing_contract.functions.getRoutingTable().call()

        table = Table(title="Routing Table")
        table.add_column("Category", style="cyan")
        table.add_column("Model")
        table.add_column("Provider")
        table.add_column("Latency", justify="right")
        table.add_column("Cost/1K", justify="right")
        table.add_column("Accuracy", justify="right")
        table.add_column("Found By")
        table.add_column("Updated")

        for route in routes:
            table.add_row(
                route[0], route[1], route[2],
                f"{route[3]}ms", f"${route[4]:.4f}",
                f"{route[5]:.2f}", route[6][:10] + "...",
                route[7],
            )

        console.print(table)

    def stats(self):
        """Display routing stats for this agent."""
        self._print_stats()

    def _execute_inference(self, provider: ProviderConfig, model: str, prompt: str) -> dict:
        """Execute inference on a specific provider/model. Dispatches to provider SDK."""
        # Provider dispatch — each returns {output, tokens_used, cost, confidence}
        if provider.name == "openai":
            return self._call_openai(model, prompt)
        elif provider.name == "anthropic":
            return self._call_anthropic(model, prompt)
        elif provider.name == "together":
            return self._call_together(model, prompt)
        elif provider.name == "local":
            return self._call_local(model, prompt)
        raise ValueError(f"Unknown provider: {provider.name}")

    def _call_openai(self, model: str, prompt: str) -> dict:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return {
            "output": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "cost": self._estimate_cost(model, response.usage.total_tokens),
            "confidence": 1.0,
        }

    def _call_anthropic(self, model: str, prompt: str) -> dict:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "output": response.content[0].text,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "cost": self._estimate_cost(model, response.usage.input_tokens + response.usage.output_tokens),
            "confidence": 1.0,
        }

    def _call_together(self, model: str, prompt: str) -> dict:
        import httpx
        import os
        response = httpx.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['TOGETHER_API_KEY']}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000},
        )
        data = response.json()
        return {
            "output": data["choices"][0]["message"]["content"],
            "tokens_used": data["usage"]["total_tokens"],
            "cost": self._estimate_cost(model, data["usage"]["total_tokens"]),
            "confidence": 1.0,
        }

    def _call_local(self, model: str, prompt: str) -> dict:
        import httpx
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        data = response.json()
        tokens = len(data.get("response", "").split()) * 1.3  # rough estimate
        return {
            "output": data["response"],
            "tokens_used": int(tokens),
            "cost": 0.0,
            "confidence": 1.0,
        }

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """Rough cost estimation per 1K tokens by model."""
        costs = {
            "gpt-5.4": 0.003, "gpt-5.4-mini": 0.0004, "gpt-4o": 0.005,
            "claude-4-sonnet": 0.003, "claude-4-haiku": 0.0008,
            "llama-3.3-70b": 0.0009, "deepseek-v3": 0.0014,
        }
        per_1k = costs.get(model, 0.002)
        return per_1k * (tokens / 1000)

    def _calculate_improvement(self, current_best: Optional[dict], new_route: dict) -> float:
        """Calculate improvement percentage over current best route."""
        if not current_best:
            return 100.0  # First route is always an improvement

        # Weighted score: 50% latency, 30% accuracy, 20% cost
        old_score = (
            (1000 / max(current_best["latency_ms"], 1)) * 0.5
            + current_best["accuracy"] * 0.3
            + (1 / max(current_best["cost_per_1k"], 0.0001)) * 0.2
        )
        new_score = (
            (1000 / max(new_route["latency_ms"], 1)) * 0.5
            + new_route["accuracy"] * 0.3
            + (1 / max(new_route["cost_per_1k"], 0.0001)) * 0.2
        )

        if old_score == 0:
            return 100.0
        return ((new_score - old_score) / old_score) * 100

    def _generate_routing_proof(self, category: TaskCategory, route: dict) -> bytes:
        message = Web3.solidity_keccak(
            ["string", "string", "string", "uint256", "address"],
            [category.value, route["model"], route["provider"], route["latency_ms"], self.address],
        )
        signed = self.account.signHash(message)
        return signed.signature

    def _print_stats(self):
        console.print()
        console.print("[bold]Routing Stats[/bold]")
        console.print(f"  Benchmarks run: {self._stats.total_benchmarks}")
        console.print(f"  Discoveries: {self._stats.total_discoveries}")
        console.print(f"  Total earned: {format_token_amount(self._stats.total_earned)} CLAWMINE")
        console.print(f"  Current streak: {self._stats.current_streak}")


@dataclass
class RoutingStats:
    total_benchmarks: int = 0
    total_discoveries: int = 0
    total_earned: int = 0
    current_streak: int = 0
    discoveries: list = field(default_factory=list)

    def record_discovery(self, category: TaskCategory, route: dict):
        self.total_discoveries += 1
        self.total_earned += route.get("reward", 0)
        self.current_streak += 1
        self.discoveries.append({
            "category": category.value,
            "model": route["model"],
            "provider": route["provider"],
            "improvement": route["improvement"],
            "timestamp": time.time(),
        })

"""
ClawMiner — Compute module.

Access the peer-to-peer inference marketplace. Spend CLAWCREDIT on
decentralized AI compute — no API key needed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator

import httpx
from web3 import Web3
from eth_account import Account

from clawminer.utils import get_web3, load_contract


COMPUTE_COORDINATOR_URL = "https://compute.clawminer.tech"


@dataclass
class InferenceResponse:
    model: str
    output: str
    tokens_used: int
    cost_clawcredit: float
    provider: str
    latency_ms: int


@dataclass
class Provider:
    address: str
    name: Optional[str]
    models: list[str]
    quality_score: float
    active: bool
    total_served: int
    avg_latency_ms: int


class ComputeClient:
    """
    Access the ClawMiner compute marketplace.

    Usage:
        client = ComputeClient(private_key="0x...")
        response = client.inference(
            model="llama-3.3-70b",
            prompt="Explain quantum computing",
        )
        print(response.output)
    """

    def __init__(
        self,
        private_key: str,
        rpc_url: str = "https://mainnet.base.org",
        coordinator_url: str = COMPUTE_COORDINATOR_URL,
    ):
        self.w3 = get_web3(rpc_url)
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.coordinator_url = coordinator_url

        self._credit_contract = load_contract(self.w3, "ClawCredit")
        self._compute_contract = load_contract(self.w3, "ComputeMarket")
        self._http = httpx.Client(timeout=60)

    def inference(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> InferenceResponse:
        """
        Run inference through the compute marketplace.

        Args:
            model: Model to use (e.g., 'llama-3.3-70b', 'gpt-5.4', 'claude-4-sonnet').
            prompt: The input prompt.
            max_tokens: Max output tokens.
            temperature: Sampling temperature.
            system: Optional system prompt.

        Returns:
            InferenceResponse with output and metadata.
        """
        # Sign the request for authentication
        message = Web3.solidity_keccak(
            ["address", "string", "uint256"],
            [self.address, model, max_tokens],
        )
        signature = self.account.signHash(message).signature.hex()

        response = self._http.post(
            f"{self.coordinator_url}/v1/inference",
            json={
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "wallet": self.address,
                "signature": signature,
            },
        )
        response.raise_for_status()
        data = response.json()

        return InferenceResponse(
            model=data["model"],
            output=data["output"],
            tokens_used=data["tokens_used"],
            cost_clawcredit=data["cost"],
            provider=data["provider"],
            latency_ms=data["latency_ms"],
        )

    async def inference_stream(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream inference output token by token."""
        message = Web3.solidity_keccak(
            ["address", "string", "uint256"],
            [self.address, model, max_tokens],
        )
        signature = self.account.signHash(message).signature.hex()

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.coordinator_url}/v1/inference/stream",
                json={
                    "model": model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system,
                    "wallet": self.address,
                    "signature": signature,
                },
            ) as response:
                async for chunk in response.aiter_text():
                    yield chunk

    def list_providers(self) -> list[Provider]:
        """List all available compute providers."""
        response = self._http.get(f"{self.coordinator_url}/v1/providers")
        response.raise_for_status()
        return [
            Provider(
                address=p["address"],
                name=p.get("name"),
                models=p["models"],
                quality_score=p["quality_score"],
                active=p["active"],
                total_served=p["total_served"],
                avg_latency_ms=p["avg_latency_ms"],
            )
            for p in response.json()["providers"]
        ]

    def get_models(self) -> list[str]:
        """List all models currently available on the network."""
        response = self._http.get(f"{self.coordinator_url}/v1/models")
        response.raise_for_status()
        return response.json()["models"]

    def clawcredit_balance(self) -> float:
        """Get current CLAWCREDIT balance."""
        raw = self._credit_contract.functions.balanceOf(self.address).call()
        return raw / 10**18

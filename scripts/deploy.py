"""
ClawMiner — Contract deployment script.

Deploys all protocol contracts to Base L2.

Usage:
    python scripts/deploy.py --network base-sepolia
    python scripts/deploy.py --network base-mainnet
"""

import argparse
import json
import os
import sys

from web3 import Web3
from eth_account import Account


NETWORKS = {
    "base-sepolia": {
        "rpc": "https://sepolia.base.org",
        "chain_id": 84532,
        "explorer": "https://sepolia.basescan.org",
    },
    "base-mainnet": {
        "rpc": "https://mainnet.base.org",
        "chain_id": 8453,
        "explorer": "https://basescan.org",
    },
}

DEPLOY_ORDER = [
    "ClawMine",
    "Treasury",
    "TaskValidator",
    "Staking",
    "Vault",
    "ClawCredit",
    "ComputeMarket",
]


def deploy(network: str, private_key: str):
    config = NETWORKS[network]
    w3 = Web3(Web3.HTTPProvider(config["rpc"]))
    account = Account.from_key(private_key)

    print(f"Deploying to {network}")
    print(f"  RPC: {config['rpc']}")
    print(f"  Chain ID: {config['chain_id']}")
    print(f"  Deployer: {account.address}")
    print(f"  Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    print()

    deployed = {}

    for contract_name in DEPLOY_ORDER:
        print(f"Deploying {contract_name}...", end=" ")

        # TODO: Load compiled contract artifacts
        # artifact_path = f"artifacts/{contract_name}.json"
        # with open(artifact_path) as f:
        #     artifact = json.load(f)

        # contract = w3.eth.contract(
        #     abi=artifact["abi"],
        #     bytecode=artifact["bytecode"],
        # )

        # tx = contract.constructor(...).build_transaction({...})
        # signed = account.sign_transaction(tx)
        # tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # deployed[contract_name] = receipt.contractAddress
        # print(f"✓ {receipt.contractAddress}")

        print("⏳ (compile contracts first)")

    print()
    print("Deployed addresses:")
    for name, addr in deployed.items():
        print(f"  {name}: {addr}")

    # Save addresses
    with open("deployed_addresses.json", "w") as f:
        json.dump({"network": network, "contracts": deployed}, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ClawMiner contracts")
    parser.add_argument("--network", choices=NETWORKS.keys(), required=True)
    args = parser.parse_args()

    private_key = os.environ.get("CLAWMINE_PRIVATE_KEY")
    if not private_key:
        print("Error: Set CLAWMINE_PRIVATE_KEY environment variable")
        sys.exit(1)

    deploy(args.network, private_key)

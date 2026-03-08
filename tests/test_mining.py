"""
Tests for ClawMiner mining module.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestMinerConfig:
    def test_default_config(self):
        from clawminer.miner import MinerConfig

        config = MinerConfig(private_key="0x" + "a" * 64)
        assert config.llm_provider == "openai"
        assert config.max_gas_per_tx == 0.001
        assert config.auto_claim is False
        assert config.min_confidence == 0.8

    def test_custom_config(self):
        from clawminer.miner import MinerConfig

        config = MinerConfig(
            private_key="0x" + "a" * 64,
            llm_provider="anthropic",
            model="claude-sonnet-4-20250514",
            max_gas_per_tx=0.005,
            auto_claim=True,
        )
        assert config.llm_provider == "anthropic"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_gas_per_tx == 0.005


class TestTaskTypes:
    def test_task_types_exist(self):
        from clawminer.miner import TaskType

        assert TaskType.CLASSIFICATION.value == "classification"
        assert TaskType.SUMMARIZATION.value == "summarization"
        assert TaskType.REASONING.value == "reasoning"
        assert TaskType.CODE_REVIEW.value == "code_review"
        assert TaskType.MULTI_HOP_QA.value == "multi_hop_qa"

    def test_difficulty_levels(self):
        from clawminer.miner import Difficulty

        assert Difficulty.EASY.value == "easy"
        assert Difficulty.MEDIUM.value == "medium"
        assert Difficulty.HARD.value == "hard"


class TestMinerStats:
    def test_empty_stats(self):
        from clawminer.miner import MinerStats

        stats = MinerStats()
        assert stats.total_solved == 0
        assert stats.total_earned == 0
        assert stats.avg_inference_ms == 0
        assert stats.avg_confidence == 0.0

    def test_record_stats(self):
        from clawminer.miner import MinerStats

        stats = MinerStats()
        stats.record(
            {"reward_estimate": 1000},
            {"inference_time_ms": 200, "confidence": 0.95},
        )
        stats.record(
            {"reward_estimate": 2000},
            {"inference_time_ms": 300, "confidence": 0.85},
        )

        assert stats.total_solved == 2
        assert stats.total_earned == 3000
        assert stats.avg_inference_ms == 250
        assert stats.avg_confidence == pytest.approx(0.9)


class TestStakingTiers:
    def test_tier_properties(self):
        from clawminer.staker import StakingTier

        spark = StakingTier.SPARK
        assert spark.required == 1_000_000
        assert spark.lock_days == 7
        assert spark.boost == 1.1
        assert spark.collateral_pct == 225

        architect = StakingTier.ARCHITECT
        assert architect.required == 500_000_000
        assert architect.lock_days == 180
        assert architect.boost == 2.0
        assert architect.collateral_pct == 150


class TestUtils:
    def test_format_token_amount(self):
        from clawminer.utils import format_token_amount

        assert format_token_amount(1_000_000 * 10**18) == "1.00M"
        assert format_token_amount(5_000 * 10**18) == "5.0K"
        assert format_token_amount(500 * 10**18) == "500"

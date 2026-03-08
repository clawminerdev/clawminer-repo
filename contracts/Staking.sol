// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title Staking
 * @notice Stake $CLAWMINE into tiers for mining boosts, passive yield, 
 *         and improved vault collateral ratios.
 *
 *         Tiers:
 *           Spark     — 1M    — 7d lock   — 1.10x boost — 225% collateral
 *           Circuit   — 5M    — 30d lock  — 1.25x boost — 200% collateral
 *           Core      — 50M   — 90d lock  — 1.50x boost — 175% collateral
 *           Architect — 500M  — 180d lock — 2.00x boost — 150% collateral
 */
contract Staking is Ownable, ReentrancyGuard {
    IERC20 public clawmine;

    enum Tier { None, Spark, Circuit, Core, Architect }

    struct TierConfig {
        uint256 required;       // Minimum tokens (in wei)
        uint256 lockDuration;   // Lock period in seconds
        uint256 boostBps;       // Mining boost in basis points (11000 = 1.1x)
        uint256 collateralPct;  // Required vault collateral %
        uint256 yieldWeight;    // Relative yield weight
    }

    struct Position {
        uint256 amount;
        Tier tier;
        uint256 stakedAt;
        uint256 lockUntil;
        uint256 accumulatedYield;
        uint256 lastYieldClaim;
    }

    mapping(Tier => TierConfig) public tierConfigs;
    mapping(address => Position) public positions;

    uint256 public totalStaked;
    uint256 public totalStakers;
    uint256 public dailyYieldPool;

    event Staked(address indexed user, uint256 amount, Tier tier);
    event Unstaked(address indexed user, uint256 amount);
    event YieldClaimed(address indexed user, uint256 amount);

    error InsufficientAmount();
    error LockNotExpired();
    error NoPosition();

    constructor(address _clawmine) Ownable(msg.sender) {
        clawmine = IERC20(_clawmine);

        tierConfigs[Tier.Spark] = TierConfig({
            required: 1_000_000 * 10**18,
            lockDuration: 7 days,
            boostBps: 11000,
            collateralPct: 225,
            yieldWeight: 100
        });

        tierConfigs[Tier.Circuit] = TierConfig({
            required: 5_000_000 * 10**18,
            lockDuration: 30 days,
            boostBps: 12500,
            collateralPct: 200,
            yieldWeight: 150
        });

        tierConfigs[Tier.Core] = TierConfig({
            required: 50_000_000 * 10**18,
            lockDuration: 90 days,
            boostBps: 15000,
            collateralPct: 175,
            yieldWeight: 250
        });

        tierConfigs[Tier.Architect] = TierConfig({
            required: 500_000_000 * 10**18,
            lockDuration: 180 days,
            boostBps: 20000,
            collateralPct: 150,
            yieldWeight: 400
        });
    }

    /**
     * @notice Stake $CLAWMINE into a tier.
     */
    function stake(uint256 amount, Tier tier) external nonReentrant {
        TierConfig memory config = tierConfigs[tier];
        if (amount < config.required) revert InsufficientAmount();

        clawmine.transferFrom(msg.sender, address(this), amount);

        if (positions[msg.sender].amount == 0) {
            totalStakers++;
        }

        positions[msg.sender] = Position({
            amount: amount,
            tier: tier,
            stakedAt: block.timestamp,
            lockUntil: block.timestamp + config.lockDuration,
            accumulatedYield: 0,
            lastYieldClaim: block.timestamp
        });

        totalStaked += amount;

        emit Staked(msg.sender, amount, tier);
    }

    /**
     * @notice Unstake all tokens. Lock period must be expired.
     */
    function unstake() external nonReentrant {
        Position storage pos = positions[msg.sender];
        if (pos.amount == 0) revert NoPosition();
        if (block.timestamp < pos.lockUntil) revert LockNotExpired();

        uint256 amount = pos.amount;
        totalStaked -= amount;
        totalStakers--;

        delete positions[msg.sender];
        clawmine.transfer(msg.sender, amount);

        emit Unstaked(msg.sender, amount);
    }

    /**
     * @notice Claim accumulated staking yield.
     */
    function claimYield() external nonReentrant {
        Position storage pos = positions[msg.sender];
        if (pos.amount == 0) revert NoPosition();

        uint256 yield_ = pos.accumulatedYield;
        pos.accumulatedYield = 0;
        pos.lastYieldClaim = block.timestamp;

        clawmine.transfer(msg.sender, yield_);

        emit YieldClaimed(msg.sender, yield_);
    }

    /**
     * @notice Get the mining boost for a miner (called by TaskValidator).
     * @return Boost in basis points (10000 = 1x, 11000 = 1.1x, etc.)
     */
    function getMiningBoost(address miner) external view returns (uint256) {
        Position storage pos = positions[miner];
        if (pos.amount == 0) return 10000; // 1x (no boost)
        return tierConfigs[pos.tier].boostBps;
    }

    /**
     * @notice Get required collateral ratio for a user's vault.
     * @return Collateral percentage (e.g., 225 = 225%)
     */
    function getCollateralRatio(address user) external view returns (uint256) {
        Position storage pos = positions[user];
        if (pos.amount == 0) return 250; // Default: 250%
        return tierConfigs[pos.tier].collateralPct;
    }

    /**
     * @notice Get position details for a user.
     */
    function getPosition(address user) external view returns (
        uint256 amount,
        uint8 tier,
        uint256 lockUntil,
        uint256 accumulatedYield,
        uint256 boostBps
    ) {
        Position storage pos = positions[user];
        return (
            pos.amount,
            uint8(pos.tier),
            pos.lockUntil,
            pos.accumulatedYield,
            pos.amount > 0 ? tierConfigs[pos.tier].boostBps : 10000
        );
    }
}

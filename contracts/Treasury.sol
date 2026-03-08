// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IClawMine {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function burn(uint256 amount) external;
}

/**
 * @title Treasury
 * @notice Manages $CLAWMINE emissions for mining rewards.
 *         Emits 0.5% of balance daily, distributed across successful miners.
 */
contract Treasury is Ownable, ReentrancyGuard {
    IClawMine public clawmine;

    uint256 public constant DAILY_EMISSION_BPS = 50; // 0.5% = 50 basis points
    uint256 public constant CLAIM_FEE_BPS = 200;     // 2% claim fee
    uint256 public constant BPS_DENOMINATOR = 10000;

    uint256 public lastEmissionTimestamp;
    uint256 public currentEpoch;
    uint256 public epochDuration = 30 minutes;

    // epoch => total rewards available
    mapping(uint256 => uint256) public epochRewards;
    // epoch => total successful solves
    mapping(uint256 => uint256) public epochSolves;
    // address => unclaimed rewards
    mapping(address => uint256) public unclaimedRewards;
    // address => total lifetime earnings
    mapping(address => uint256) public lifetimeEarnings;

    address public validator;
    address public stakingContract;

    uint256 public totalDistributed;
    uint256 public totalBurned;

    event RewardsDistributed(uint256 indexed epoch, uint256 amount, uint256 solves);
    event RewardsClaimed(address indexed miner, uint256 amount, uint256 fee);
    event EpochAdvanced(uint256 indexed epoch, uint256 emission);

    error OnlyValidator();
    error NothingToClaim();

    modifier onlyValidator() {
        if (msg.sender != validator) revert OnlyValidator();
        _;
    }

    constructor(address _clawmine) Ownable(msg.sender) {
        clawmine = IClawMine(_clawmine);
        lastEmissionTimestamp = block.timestamp;
    }

    /**
     * @notice Set the validator contract.
     */
    function setValidator(address _validator) external onlyOwner {
        validator = _validator;
    }

    /**
     * @notice Set the staking contract for yield distribution.
     */
    function setStakingContract(address _staking) external onlyOwner {
        stakingContract = _staking;
    }

    /**
     * @notice Calculate current daily emission amount.
     */
    function dailyEmission() public view returns (uint256) {
        uint256 balance = clawmine.balanceOf(address(this));
        return (balance * DAILY_EMISSION_BPS) / BPS_DENOMINATOR;
    }

    /**
     * @notice Credit mining rewards to a miner. Called by TaskValidator.
     */
    function creditReward(address miner, uint256 amount) external onlyValidator {
        unclaimedRewards[miner] += amount;
        lifetimeEarnings[miner] += amount;
        epochSolves[currentEpoch]++;
        totalDistributed += amount;
    }

    /**
     * @notice Claim accumulated mining rewards.
     */
    function claimRewards() external nonReentrant {
        uint256 amount = unclaimedRewards[msg.sender];
        if (amount == 0) revert NothingToClaim();

        unclaimedRewards[msg.sender] = 0;

        // 2% claim fee stays in treasury
        uint256 fee = (amount * CLAIM_FEE_BPS) / BPS_DENOMINATOR;
        uint256 payout = amount - fee;

        clawmine.transfer(msg.sender, payout);

        // 80% of staking yield comes from emissions
        // 20% of daily emission goes to stakers
        if (stakingContract != address(0)) {
            uint256 stakingYield = (fee * 5000) / BPS_DENOMINATOR; // 50% of fee to stakers
            clawmine.transfer(stakingContract, stakingYield);
        }

        emit RewardsClaimed(msg.sender, payout, fee);
    }

    /**
     * @notice Advance to next epoch and calculate new emission.
     */
    function advanceEpoch() external {
        require(
            block.timestamp >= lastEmissionTimestamp + epochDuration,
            "Epoch not elapsed"
        );

        currentEpoch++;
        uint256 emission = dailyEmission() / (1 days / epochDuration);
        epochRewards[currentEpoch] = emission;
        lastEmissionTimestamp = block.timestamp;

        emit EpochAdvanced(currentEpoch, emission);
    }
}

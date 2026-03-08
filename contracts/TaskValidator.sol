// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

interface ITreasury {
    function creditReward(address miner, uint256 amount) external;
    function dailyEmission() external view returns (uint256);
    function epochSolves(uint256 epoch) external view returns (uint256);
    function currentEpoch() external view returns (uint256);
}

interface IStaking {
    function getMiningBoost(address miner) external view returns (uint256);
}

/**
 * @title TaskValidator
 * @notice Validates inference task solutions and distributes mining rewards.
 *         Tasks are generated off-chain, solutions are verified on-chain
 *         through deterministic validation and proof verification.
 */
contract TaskValidator is Ownable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    ITreasury public treasury;
    IStaking public staking;

    uint256 public taskCounter;
    uint256 public totalSolves;
    uint256 public minStakeToMine = 5_000_000 * 10**18; // 5M CLAWMINE

    enum TaskType { Classification, Summarization, Reasoning, CodeReview, MultiHopQA }
    enum Difficulty { Easy, Medium, Hard }

    struct Task {
        uint256 id;
        TaskType taskType;
        Difficulty difficulty;
        bytes32 payloadHash;
        bytes32 expectedOutputHash;
        uint256 rewardEstimate;
        bool solved;
        address solver;
    }

    // taskId => Task
    mapping(uint256 => Task) public tasks;
    // address => total solves
    mapping(address => uint256) public minerSolves;
    // address => last solve timestamp (cooldown)
    mapping(address => uint256) public lastSolveTime;

    // Difficulty multipliers (in basis points, 10000 = 1x)
    mapping(Difficulty => uint256) public difficultyMultiplier;

    uint256 public cooldownSeconds = 5;

    // Trusted task generators (off-chain oracles)
    mapping(address => bool) public taskGenerators;

    event TaskCreated(uint256 indexed taskId, TaskType taskType, Difficulty difficulty);
    event TaskSolved(uint256 indexed taskId, address indexed solver, uint256 reward);
    event DifficultyAdjusted(uint256 activeMinerCount);

    error TaskAlreadySolved();
    error InvalidProof();
    error InsufficientStake();
    error CooldownActive();
    error OnlyTaskGenerator();

    modifier onlyTaskGenerator() {
        if (!taskGenerators[msg.sender]) revert OnlyTaskGenerator();
        _;
    }

    constructor(address _treasury) Ownable(msg.sender) {
        treasury = ITreasury(_treasury);

        difficultyMultiplier[Difficulty.Easy] = 5000;     // 0.5x
        difficultyMultiplier[Difficulty.Medium] = 10000;   // 1.0x
        difficultyMultiplier[Difficulty.Hard] = 25000;     // 2.5x
    }

    function setStaking(address _staking) external onlyOwner {
        staking = IStaking(_staking);
    }

    function addTaskGenerator(address _generator) external onlyOwner {
        taskGenerators[_generator] = true;
    }

    /**
     * @notice Create a new task (called by off-chain task generator).
     */
    function createTask(
        TaskType _type,
        Difficulty _difficulty,
        bytes32 _payloadHash,
        bytes32 _expectedOutputHash,
        uint256 _rewardEstimate
    ) external onlyTaskGenerator returns (uint256) {
        taskCounter++;
        tasks[taskCounter] = Task({
            id: taskCounter,
            taskType: _type,
            difficulty: _difficulty,
            payloadHash: _payloadHash,
            expectedOutputHash: _expectedOutputHash,
            rewardEstimate: _rewardEstimate,
            solved: false,
            solver: address(0)
        });

        emit TaskCreated(taskCounter, _type, _difficulty);
        return taskCounter;
    }

    /**
     * @notice Submit a proof for a solved task.
     * @param taskId The task ID.
     * @param output The solution output string.
     * @param proof Signed proof from the miner.
     * @param confidence Confidence score (0-1000, representing 0.000-1.000).
     */
    function submitProof(
        uint256 taskId,
        string calldata output,
        bytes calldata proof,
        uint256 confidence
    ) external {
        Task storage task = tasks[taskId];

        if (task.solved) revert TaskAlreadySolved();
        if (block.timestamp < lastSolveTime[msg.sender] + cooldownSeconds) {
            revert CooldownActive();
        }

        // Verify output matches expected hash
        bytes32 outputHash = keccak256(abi.encodePacked(output));
        if (outputHash != task.expectedOutputHash) revert InvalidProof();

        // Verify signature
        bytes32 messageHash = keccak256(
            abi.encodePacked(taskId, output, msg.sender)
        );
        bytes32 ethSignedHash = messageHash.toEthSignedMessageHash();
        address signer = ethSignedHash.recover(proof);
        if (signer != msg.sender) revert InvalidProof();

        // Mark solved
        task.solved = true;
        task.solver = msg.sender;
        totalSolves++;
        minerSolves[msg.sender]++;
        lastSolveTime[msg.sender] = block.timestamp;

        // Calculate reward with difficulty multiplier and staking boost
        uint256 baseReward = task.rewardEstimate;
        uint256 diffMultiplier = difficultyMultiplier[task.difficulty];
        uint256 reward = (baseReward * diffMultiplier) / 10000;

        // Apply staking boost
        if (address(staking) != address(0)) {
            uint256 boost = staking.getMiningBoost(msg.sender);
            reward = (reward * boost) / 10000;
        }

        // Credit reward through treasury
        treasury.creditReward(msg.sender, reward);

        emit TaskSolved(taskId, msg.sender, reward);
    }

    /**
     * @notice Get the next available task for a miner.
     */
    function getNextTask(address) external view returns (
        uint256 id,
        uint8 taskType,
        uint8 difficulty,
        bytes32 payloadHash,
        uint256 rewardEstimate
    ) {
        // Find first unsolved task (simplified — production uses merkle tree)
        for (uint256 i = taskCounter; i > 0; i--) {
            if (!tasks[i].solved) {
                Task storage t = tasks[i];
                return (
                    t.id,
                    uint8(t.taskType),
                    uint8(t.difficulty),
                    t.payloadHash,
                    t.rewardEstimate
                );
            }
        }
        revert("No tasks available");
    }
}

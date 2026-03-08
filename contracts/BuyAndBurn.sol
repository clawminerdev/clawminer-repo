// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IUniswapV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata params) external payable returns (uint256 amountOut);
}

interface IWETH {
    function deposit() external payable;
    function withdraw(uint256) external;
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
}

/**
 * @title BuyAndBurn
 * @notice Receives WETH from Clanker creator rewards, swaps for $CLAWMINE
 *         via Uniswap V3, and sends to burn address. Fully permissionless —
 *         anyone can trigger a burn cycle.
 *
 *         Flow:
 *           1. Clanker creator rewards accrue as WETH
 *           2. WETH is sent to this contract (or claimed directly here)
 *           3. Anyone calls executeBurn()
 *           4. Contract swaps all WETH balance for $CLAWMINE
 *           5. Purchased $CLAWMINE is sent to 0x...dEaD
 *           6. Burn event emitted with amount and tx details
 *
 * @dev    100% of fees go to burn. No team allocation. No admin withdrawal.
 *         The only way tokens leave this contract is to the burn address.
 */
contract BuyAndBurn is Ownable, ReentrancyGuard {
    // Immutables
    address public constant BURN_ADDRESS = 0x000000000000000000000000000000000000dEaD;
    address public immutable clawmine;
    address public immutable weth;
    address public immutable uniswapRouter;

    // Pool fee tier (Uniswap V3)
    uint24 public poolFee = 10000; // 1% — matches Clanker default pool

    // Burn tracking
    uint256 public totalBurned;
    uint256 public totalWethSpent;
    uint256 public burnCount;
    uint256 public lastBurnTimestamp;

    // Minimum WETH balance required to trigger a burn (prevents dust txs)
    uint256 public minBurnThreshold = 0.001 ether;

    // Slippage protection (basis points, 500 = 5%)
    uint256 public maxSlippageBps = 500;

    // Burn history
    struct BurnRecord {
        uint256 wethIn;
        uint256 clawmineBurned;
        uint256 timestamp;
        address triggeredBy;
    }

    BurnRecord[] public burnHistory;

    // Events
    event BurnExecuted(
        uint256 indexed burnId,
        uint256 wethSpent,
        uint256 clawmineBurned,
        address triggeredBy,
        uint256 timestamp
    );
    event ThresholdUpdated(uint256 oldThreshold, uint256 newThreshold);
    event SlippageUpdated(uint256 oldSlippage, uint256 newSlippage);
    event PoolFeeUpdated(uint24 oldFee, uint24 newFee);

    // Errors
    error InsufficientBalance();
    error BelowThreshold();
    error BurnFailed();

    constructor(
        address _clawmine,
        address _weth,
        address _uniswapRouter
    ) Ownable(msg.sender) {
        clawmine = _clawmine;
        weth = _weth;
        uniswapRouter = _uniswapRouter;
    }

    /**
     * @notice Execute a buy-and-burn cycle. Permissionless — anyone can call.
     * @dev    Swaps entire WETH balance for $CLAWMINE and sends to burn address.
     */
    function executeBurn() external nonReentrant {
        uint256 wethBalance = IWETH(weth).balanceOf(address(this));

        if (wethBalance == 0) revert InsufficientBalance();
        if (wethBalance < minBurnThreshold) revert BelowThreshold();

        // Approve router
        IWETH(weth).approve(uniswapRouter, wethBalance);

        // Calculate minimum output with slippage protection
        // In production, use a TWAP oracle for better price reference
        uint256 minOut = 0; // Set to 0 for now; oracle integration in v2

        // Swap WETH → CLAWMINE, send directly to burn address
        IUniswapV3Router.ExactInputSingleParams memory params = IUniswapV3Router
            .ExactInputSingleParams({
                tokenIn: weth,
                tokenOut: clawmine,
                fee: poolFee,
                recipient: BURN_ADDRESS,
                deadline: block.timestamp + 300,
                amountIn: wethBalance,
                amountOutMinimum: minOut,
                sqrtPriceLimitX96: 0
            });

        uint256 amountBurned = IUniswapV3Router(uniswapRouter).exactInputSingle(params);

        if (amountBurned == 0) revert BurnFailed();

        // Update tracking
        totalBurned += amountBurned;
        totalWethSpent += wethBalance;
        burnCount++;
        lastBurnTimestamp = block.timestamp;

        // Record history
        burnHistory.push(BurnRecord({
            wethIn: wethBalance,
            clawmineBurned: amountBurned,
            timestamp: block.timestamp,
            triggeredBy: msg.sender
        }));

        emit BurnExecuted(burnCount, wethBalance, amountBurned, msg.sender, block.timestamp);
    }

    /**
     * @notice Check if a burn can be executed (sufficient balance above threshold).
     */
    function canBurn() external view returns (bool, uint256) {
        uint256 balance = IWETH(weth).balanceOf(address(this));
        return (balance >= minBurnThreshold, balance);
    }

    /**
     * @notice Get the full burn history.
     */
    function getBurnHistory() external view returns (BurnRecord[] memory) {
        return burnHistory;
    }

    /**
     * @notice Get the most recent burn record.
     */
    function getLastBurn() external view returns (BurnRecord memory) {
        require(burnHistory.length > 0, "No burns yet");
        return burnHistory[burnHistory.length - 1];
    }

    /**
     * @notice Get burn stats summary.
     */
    function getBurnStats() external view returns (
        uint256 _totalBurned,
        uint256 _totalWethSpent,
        uint256 _burnCount,
        uint256 _lastBurnTimestamp,
        uint256 _pendingWeth
    ) {
        return (
            totalBurned,
            totalWethSpent,
            burnCount,
            lastBurnTimestamp,
            IWETH(weth).balanceOf(address(this))
        );
    }

    // --- Admin functions (owner only) ---

    function setMinBurnThreshold(uint256 _threshold) external onlyOwner {
        emit ThresholdUpdated(minBurnThreshold, _threshold);
        minBurnThreshold = _threshold;
    }

    function setMaxSlippage(uint256 _bps) external onlyOwner {
        require(_bps <= 2000, "Slippage too high"); // Max 20%
        emit SlippageUpdated(maxSlippageBps, _bps);
        maxSlippageBps = _bps;
    }

    function setPoolFee(uint24 _fee) external onlyOwner {
        emit PoolFeeUpdated(poolFee, _fee);
        poolFee = _fee;
    }

    // Accept ETH (auto-wrap to WETH)
    receive() external payable {
        IWETH(weth).deposit{value: msg.value}();
    }
}

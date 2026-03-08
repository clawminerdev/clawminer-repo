// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title ClawMine
 * @notice ERC-20 token for the ClawMiner proof-of-inference mining protocol.
 * @dev Total supply: 100 billion (100,000,000,000 * 10^18)
 *      Initial liquidity: 50,000,000 tokens minted to deployer.
 *      Remaining supply held in Treasury for mining emissions.
 */
contract ClawMine is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 100_000_000_000 * 10**18;
    uint256 public constant INITIAL_LIQUIDITY = 50_000_000 * 10**18;

    address public treasury;
    
    mapping(address => bool) public minters;

    event TreasurySet(address indexed treasury);
    event MinterAdded(address indexed minter);
    event MinterRemoved(address indexed minter);

    error ExceedsMaxSupply();
    error NotMinter();
    error ZeroAddress();

    constructor() ERC20("ClawMine", "CLAWMINE") Ownable(msg.sender) {
        _mint(msg.sender, INITIAL_LIQUIDITY);
    }

    /**
     * @notice Set the treasury contract address.
     * @param _treasury Address of the Treasury contract.
     */
    function setTreasury(address _treasury) external onlyOwner {
        if (_treasury == address(0)) revert ZeroAddress();
        treasury = _treasury;
        emit TreasurySet(_treasury);

        // Mint remaining supply to treasury
        uint256 remaining = MAX_SUPPLY - totalSupply();
        if (remaining > 0) {
            _mint(_treasury, remaining);
        }
    }

    /**
     * @notice Add a minter (Treasury or Staking contract).
     */
    function addMinter(address _minter) external onlyOwner {
        if (_minter == address(0)) revert ZeroAddress();
        minters[_minter] = true;
        emit MinterAdded(_minter);
    }

    /**
     * @notice Remove a minter.
     */
    function removeMinter(address _minter) external onlyOwner {
        minters[_minter] = false;
        emit MinterRemoved(_minter);
    }

    /**
     * @notice Burn tokens. Anyone can burn their own tokens.
     * @param amount Amount to burn.
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }

    /**
     * @notice Burn tokens from an address (requires allowance).
     * @param from Address to burn from.
     * @param amount Amount to burn.
     */
    function burnFrom(address from, uint256 amount) external {
        _spendAllowance(from, msg.sender, amount);
        _burn(from, amount);
    }
}

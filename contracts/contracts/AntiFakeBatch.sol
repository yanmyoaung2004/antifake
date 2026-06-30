// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract AntiFakeBatch {
    address public backendSigner;

    struct Batch {
        bytes32 merkleRoot;
        bytes32 regionHash;
        uint256 mintedAt;
        bool exists;
    }

    event BatchMinted(
        bytes32 indexed batchId,
        bytes32 merkleRoot,
        bytes32 regionHash,
        uint256 mintedAt
    );

    event ScanRecorded(
        bytes32 indexed batchId,
        string serial,
        address indexed scanner,
        bytes32 gpsHash,
        uint256 timestamp
    );

    mapping(bytes32 => Batch) public batches;
    mapping(bytes32 => mapping(string => bool)) public serialUsed;

    modifier onlyBackend() {
        require(msg.sender == backendSigner, "not backend");
        _;
    }

    constructor(address _backendSigner) {
        backendSigner = _backendSigner;
    }

    function mintBatch(
        bytes32 batchId,
        bytes32 merkleRoot,
        bytes32 regionHash
    ) external onlyBackend {
        require(!batches[batchId].exists, "batch exists");
        batches[batchId] = Batch({
            merkleRoot: merkleRoot,
            regionHash: regionHash,
            mintedAt: block.timestamp,
            exists: true
        });
        emit BatchMinted(batchId, merkleRoot, regionHash, block.timestamp);
    }

    function verifySerial(
        bytes32 batchId,
        string calldata serial,
        bytes32[] calldata proof
    ) external view returns (bool) {
        require(batches[batchId].exists, "batch not found");
        bytes32 leaf = keccak256(abi.encodePacked(serial));
        bytes32 computedRoot = processProof(proof, leaf);
        return computedRoot == batches[batchId].merkleRoot;
    }

    function recordScan(
        bytes32 batchId,
        string calldata serial,
        bytes32 gpsHash
    ) external onlyBackend {
        require(batches[batchId].exists, "batch not found");
        require(!serialUsed[batchId][serial], "serial already scanned");
        serialUsed[batchId][serial] = true;
        emit ScanRecorded(batchId, serial, msg.sender, gpsHash, block.timestamp);
    }

    function processProof(
        bytes32[] memory proof,
        bytes32 leaf
    ) private pure returns (bytes32) {
        bytes32 computedHash = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            computedHash = computedHash < proof[i]
                ? keccak256(abi.encodePacked(computedHash, proof[i]))
                : keccak256(abi.encodePacked(proof[i], computedHash));
        }
        return computedHash;
    }
}

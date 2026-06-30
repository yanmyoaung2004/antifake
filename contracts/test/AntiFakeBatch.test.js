const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AntiFakeBatch", function () {
  let contract, backend, user;

  beforeEach(async () => {
    [backend, user] = await ethers.getSigners();
    const AntiFakeBatch = await ethers.getContractFactory("AntiFakeBatch");
    contract = await AntiFakeBatch.deploy(backend.address);
    await contract.waitForDeployment();
  });

  it("should mint a batch", async () => {
    const batchId = ethers.id("BATCH-A");
    const root = ethers.randomBytes(32);
    const region = ethers.id("MYANMAR");
    await contract.connect(backend).mintBatch(batchId, root, region);
    const batch = await contract.batches(batchId);
    expect(batch.exists).to.be.true;
  });

  it("should reject duplicate batch mint", async () => {
    const batchId = ethers.id("BATCH-A");
    const root = ethers.randomBytes(32);
    const region = ethers.id("MYANMAR");
    await contract.connect(backend).mintBatch(batchId, root, region);
    await expect(
      contract.connect(backend).mintBatch(batchId, root, region)
    ).to.be.revertedWith("batch exists");
  });

  it("should reject mint from non-backend", async () => {
    const batchId = ethers.id("BATCH-A");
    const root = ethers.randomBytes(32);
    const region = ethers.id("MYANMAR");
    await expect(
      contract.connect(user).mintBatch(batchId, root, region)
    ).to.be.revertedWith("not backend");
  });

  it("should record a scan", async () => {
    const batchId = ethers.id("BATCH-A");
    const root = ethers.randomBytes(32);
    const region = ethers.id("MYANMAR");
    await contract.connect(backend).mintBatch(batchId, root, region);
    const gpsHash = ethers.id("21.9731,96.0836");
    await expect(
      contract.connect(backend).recordScan(batchId, "SERIAL-001", gpsHash)
    )
      .to.emit(contract, "ScanRecorded")
      .withArgs(batchId, "SERIAL-001", backend.address, gpsHash, anyValue);
  });

  it("should reject duplicate scan", async () => {
    const batchId = ethers.id("BATCH-A");
    const root = ethers.randomBytes(32);
    const region = ethers.id("MYANMAR");
    await contract.connect(backend).mintBatch(batchId, root, region);
    await contract.connect(backend).recordScan(batchId, "SERIAL-001", ethers.id("GPS"));
    await expect(
      contract.connect(backend).recordScan(batchId, "SERIAL-001", ethers.id("GPS"))
    ).to.be.revertedWith("serial already scanned");
  });

  it("should verify a serial via Merkle proof", async () => {
    const serials = ["SERIAL-001", "SERIAL-002", "SERIAL-003", "SERIAL-004"];
    const leaves = serials.map(s => ethers.solidityPackedKeccak256(["string"], [s]));
    const merkleTree = buildMerkleTree(leaves);
    const root = merkleTree[merkleTree.length - 1][0];
    const batchId = ethers.id("BATCH-A");
    const region = ethers.id("MYANMAR");

    await contract.connect(backend).mintBatch(batchId, root, region);
    const proof = getProof(merkleTree, 0);
    const result = await contract.verifySerial(batchId, "SERIAL-001", proof);
    expect(result).to.be.true;

    const badProof = getProof(merkleTree, 1);
    const badResult = await contract.verifySerial(batchId, "SERIAL-001", badProof);
    expect(badResult).to.be.false;
  });
});

function buildMerkleTree(leaves) {
  let row = leaves;
  const tree = [row];
  while (row.length > 1) {
    const next = [];
    for (let i = 0; i < row.length; i += 2) {
      const a = row[i];
      const b = i + 1 < row.length ? row[i + 1] : a;
      next.push(ethers.solidityPackedKeccak256(["bytes32", "bytes32"], [a, b].sort()));
    }
    tree.push(next);
    row = next;
  }
  return tree;
}

function getProof(tree, index) {
  const proof = [];
  let idx = index;
  for (let level = 0; level < tree.length - 1; level++) {
    const siblings = tree[level];
    const pairIdx = idx % 2 === 0 ? idx + 1 : idx - 1;
    if (pairIdx < siblings.length) {
      proof.push(siblings[pairIdx]);
    }
    idx = Math.floor(idx / 2);
  }
  return proof;
}

const anyValue = (...args) => true;

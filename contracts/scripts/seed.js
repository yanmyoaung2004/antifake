const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

const BATCHES = [
  { id: "BATCH-A", region: "MYANMAR", count: 200 },
  { id: "BATCH-B", region: "VIETNAM", count: 150 },
  { id: "BATCH-C", region: "THAILAND", count: 150 },
];

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const AntiFakeBatch = await hre.ethers.getContractFactory("AntiFakeBatch");
  const contract = AntiFakeBatch.attach(process.env.CONTRACT_ADDRESS);

  const allData = [];

  for (const batch of BATCHES) {
    const serials = [];
    for (let i = 1; i <= batch.count; i++) {
      serials.push(`${batch.id}-${String(i).padStart(4, "0")}`);
    }

    const leaves = serials.map((s) =>
      hre.ethers.solidityPackedKeccak256(["string"], [s])
    );
    const root = buildMerkleRoot(leaves);
    const batchId = hre.ethers.id(batch.id);
    const regionHash = hre.ethers.id(batch.region);

    const tx = await contract.mintBatch(batchId, root, regionHash);
    await tx.wait();

    console.log(`Minted ${batch.id}: ${batch.count} serials, root=${root}`);

    allData.push({
      batchId: batch.id,
      region: batch.region,
      serials,
      merkleRoot: root,
      regionHash,
    });
  }

  const outDir = path.join(__dirname, "..", "data");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "seed.json"), JSON.stringify(allData, null, 2));
  console.log("Seed data written to data/seed.json");
}

function buildMerkleRoot(leaves) {
  let row = leaves;
  while (row.length > 1) {
    const next = [];
    for (let i = 0; i < row.length; i += 2) {
      const a = row[i];
      const b = i + 1 < row.length ? row[i + 1] : a;
      next.push(
        hre.ethers.solidityPackedKeccak256(
          ["bytes32", "bytes32"],
          [a, b].sort()
        )
      );
    }
    row = next;
  }
  return row[0];
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

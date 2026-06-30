const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const AntiFakeBatch = await hre.ethers.getContractFactory("AntiFakeBatch");
  const contract = await AntiFakeBatch.deploy(deployer.address);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("AntiFakeBatch deployed to:", address);
  console.log("Backend signer:", deployer.address);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});

import hashlib
import json
import os

from web3 import Web3

from app.config import settings


class BlockchainClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        self.contract = None
        self.signer = None

        abi_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "abi.json"
        )
        if settings.contract_address and os.path.exists(abi_path):
            with open(abi_path) as f:
                abi = json.load(f)
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(settings.contract_address),
                abi=abi,
            )
            accounts = self.w3.eth.accounts
            if accounts:
                self.signer = accounts[0]

    @property
    def is_connected(self) -> bool:
        return self.w3.is_connected()

    def get_batch_root(self, batch_id: str) -> bytes | None:
        if self.contract is None:
            return None
        try:
            batch_id_bytes = hashlib.sha256(batch_id.encode()).digest()
            batch = self.contract.functions.batches(batch_id_bytes).call()
            return batch[0]
        except Exception:
            return None

    def record_scan(
        self, serial: str, gps_hash: str
    ) -> str | None:
        if self.contract is None or self.signer is None:
            return None
        try:
            tx = self.contract.functions.recordScan(
                hashlib.sha256(b"dummy-batch").digest(),
                serial,
                hashlib.sha256(gps_hash.encode()).digest(),
            ).transact({"from": self.signer})
            return tx.hex()
        except Exception:
            return None


blockchain_client = BlockchainClient()

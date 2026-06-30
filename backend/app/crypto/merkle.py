import hashlib


def hash_pair(a: bytes, b: bytes) -> bytes:
    return hashlib.sha256(sorted([a, b])[0] + sorted([a, b])[1]).digest()


def generate_proof(serials: list[str], index: int) -> list[str]:
    leaves = [hashlib.sha256(s.encode()).digest() for s in serials]
    tree = [leaves]
    while len(tree[-1]) > 1:
        row = tree[-1]
        next_row = []
        for i in range(0, len(row), 2):
            a = row[i]
            b = row[i + 1] if i + 1 < len(row) else a
            next_row.append(hash_pair(a, b))
        tree.append(next_row)

    proof = []
    idx = index
    for level in range(len(tree) - 1):
        siblings = tree[level]
        pair_idx = idx + 1 if idx % 2 == 0 else idx - 1
        if pair_idx < len(siblings):
            proof.append(siblings[pair_idx].hex())
        idx //= 2

    return proof


def verify_proof(serial: str, proof: list[str], root: str) -> bool:
    leaf = hashlib.sha256(serial.encode()).digest()
    computed = leaf
    for sibling_hex in proof:
        sibling = bytes.fromhex(sibling_hex)
        computed = hash_pair(computed, sibling)
    return computed.hex() == root

import json
import os
import random

BATCHES = [
    {"id": "BATCH-A", "region": "MYANMAR", "count": 200},
    {"id": "BATCH-B", "region": "VIETNAM", "count": 150},
    {"id": "BATCH-C", "region": "THAILAND", "count": 150},
]

REGIONS = {
    "MYANMAR": {"min_lat": 10.0, "max_lat": 28.5, "min_lng": 92.0, "max_lng": 101.0},
    "VIETNAM": {"min_lat": 8.5, "max_lat": 23.5, "min_lng": 102.0, "max_lng": 110.0},
    "THAILAND": {"min_lat": 5.5, "max_lat": 20.5, "min_lng": 97.0, "max_lng": 106.0},
}


def generate_crypto_fingerprint() -> str:
    import base64
    import io

    import numpy as np
    from PIL import Image

    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(out_dir, exist_ok=True)

    batch_data = []
    for batch in BATCHES:
        serials = [
            f"{batch['id']}-{str(i).zfill(4)}" for i in range(1, batch["count"] + 1)
        ]
        fingerprints = {
            s: generate_crypto_fingerprint() for s in random.sample(serials, min(10, batch["count"]))
        }
        batch_data.append({
            "batchId": batch["id"],
            "region": batch["region"],
            "serials": serials,
            "fingerprints": fingerprints,
        })

    with open(os.path.join(out_dir, "batches.json"), "w") as f:
        json.dump(batch_data, f, indent=2)

    with open(os.path.join(out_dir, "regions.json"), "w") as f:
        json.dump(REGIONS, f, indent=2)

    print(f"Seed data generated: {sum(b['count'] for b in BATCHES)} serials across {len(BATCHES)} batches")


if __name__ == "__main__":
    main()

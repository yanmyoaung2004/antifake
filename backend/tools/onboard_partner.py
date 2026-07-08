"""
Partner onboarding: import a real supply chain into AntiFake.

This script demonstrates the /api/v1/register endpoint by importing
realistic supply chain data for partner factories. In a real deployment,
the manufacturer's ERP would call this endpoint directly to register
each batch as it's produced.

Usage:
    python tools/onboard_partner.py [--url http://localhost:8000]

Edit the PARTNERS list below to add your own factories.
"""
import argparse
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Realistic partner onboarding data. Coordinates are real, manufacturer
# and pharmacy names are illustrative (replace with your real partners).
PARTNERS = [
    {
        "batch_id": "MM-PARA-2026-07",
        "region": "MYANMAR",
        "mint_date": "2026-07-01",
        "manufacturer": "PharmaCorp Myanmar Ltd.",
        "drug_name": "Paracetamol 500mg",
        "drug_use": "Fever & Pain Relief",
        "expiry": "2028-06",
        "route": [
            {"location_name": "PharmaCorp Factory — Yangon", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
            {"location_name": "Yangon International Port", "lat": 16.7808, "lng": 96.1650, "event": "Shipped"},
            {"location_name": "Mandalay Distribution Hub", "lat": 21.9731, "lng": 96.0836, "event": "Arrived at Distributor"},
            {"location_name": "Mandalay Central Pharmacy", "lat": 21.9588, "lng": 96.0896, "event": "Delivered to Pharmacy"},
        ],
    },
    {
        "batch_id": "VN-AMOX-2026-07",
        "region": "VIETNAM",
        "mint_date": "2026-07-05",
        "manufacturer": "VinPharm Joint Stock Co.",
        "drug_name": "Amoxicillin 250mg",
        "drug_use": "Antibiotic",
        "expiry": "2028-06",
        "route": [
            {"location_name": "VinPharm Factory — Hanoi", "lat": 21.0278, "lng": 105.8342, "event": "Manufactured"},
            {"location_name": "Da Nang Logistics Hub", "lat": 16.0544, "lng": 108.2022, "event": "Transit Check"},
            {"location_name": "Ho Chi Minh City Warehouse", "lat": 10.8231, "lng": 106.6297, "event": "Arrived at Distributor"},
            {"location_name": "Saigon Central Pharmacy", "lat": 10.7769, "lng": 106.7009, "event": "Delivered to Pharmacy"},
        ],
    },
    {
        "batch_id": "TH-OME-2026-07",
        "region": "THAILAND",
        "mint_date": "2026-07-10",
        "manufacturer": "SiamPharm Co., Ltd.",
        "drug_name": "Omeprazole 20mg",
        "drug_use": "Acid Reflux",
        "expiry": "2028-06",
        "route": [
            {"location_name": "SiamPharm Factory — Bangkok", "lat": 13.7563, "lng": 100.5018, "event": "Manufactured"},
            {"location_name": "Chiang Mai Distribution Center", "lat": 18.7883, "lng": 98.9853, "event": "Arrived at Distributor"},
            {"location_name": "Phuket Regional Pharmacy", "lat": 7.8804, "lng": 98.3923, "event": "Delivered to Pharmacy"},
        ],
    },
    {
        "batch_id": "MM-IBU-2026-07",
        "region": "MYANMAR",
        "mint_date": "2026-07-15",
        "manufacturer": "PharmaCorp Myanmar Ltd.",
        "drug_name": "Ibuprofen 400mg",
        "drug_use": "Anti-inflammatory",
        "expiry": "2028-06",
        "route": [
            {"location_name": "PharmaCorp Factory — Yangon", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
            {"location_name": "Naypyidaw Central Warehouse", "lat": 19.7633, "lng": 96.0785, "event": "Arrived at Distributor"},
            {"location_name": "Naypyidaw Pharmacy 12", "lat": 19.7700, "lng": 96.0900, "event": "Delivered to Pharmacy"},
        ],
    },
    {
        "batch_id": "VN-MET-2026-07",
        "region": "VIETNAM",
        "mint_date": "2026-07-20",
        "manufacturer": "VinPharm Joint Stock Co.",
        "drug_name": "Metformin 500mg",
        "drug_use": "Diabetes",
        "expiry": "2028-07",
        "route": [
            {"location_name": "VinPharm Factory — Hanoi", "lat": 21.0278, "lng": 105.8342, "event": "Manufactured"},
            {"location_name": "Hai Phong Distribution", "lat": 20.8449, "lng": 106.6881, "event": "Arrived at Distributor"},
            {"location_name": "Hanoi Central Pharmacy", "lat": 21.0285, "lng": 105.8542, "event": "Delivered to Pharmacy"},
        ],
    },
]


def post(url: str, path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def get(url: str, path: str) -> dict:
    with urllib.request.urlopen(url + path, timeout=10) as r:
        return json.loads(r.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    print(f"\n  Onboarding {len(PARTNERS)} partner batches to {args.url}\n")

    for p in PARTNERS:
        try:
            r = post(args.url, "/api/v1/register", p)
            action = "registered" if r["inserted"] else "updated"
            print(f"  [{action}] {p['batch_id']:20s} {p['drug_name']:25s} {p['manufacturer']}")
        except Exception as e:
            print(f"  [FAIL]   {p['batch_id']:20s} {e}")

    # Show the resulting batch list
    print(f"\n  Batches now in the system:")
    try:
        result = get(args.url, "/api/v1/batches")
        for b in result["batches"]:
            extras = " ".join(
                x for x in (b.get("manufacturer", ""), b.get("drug_name", "")) if x
            )
            print(f"    {b['batch_id']:25s} {b['region']:10s} {extras}")
        print(f"\n  Total: {result['total']} batches")
    except Exception as e:
        print(f"  [WARN] could not fetch batch list: {e}")


if __name__ == "__main__":
    main()

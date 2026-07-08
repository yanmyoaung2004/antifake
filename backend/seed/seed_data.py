"""
Seeds the database with batch data and realistic supply chain routes.

Batches are based on real manufacturers and pharmacies in Myanmar,
Vietnam, and Thailand. Coordinates are real (from OpenStreetMap data).
Drug names and uses are illustrative, modeled on common regional
pharmaceutical products.

Run once: uv run python seed/seed_data.py
Re-runs are safe (existing batches are skipped).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from app.database import init_db, get_db


SUPPLY_CHAIN = {
    "BATCH-A": {
        "region": "MYANMAR",
        "mint_date": "2026-06-01",
        "manufacturer": "PharmaCorp Myanmar Ltd.",
        "drug_name": "Paracetamol 500mg",
        "drug_use": "Fever & Pain Relief",
        "expiry": "2028-05",
        "route": [
            {"point_order": 1, "location_name": "PharmaCorp Factory — Yangon", "lat": 16.8661, "lng": 96.1951, "event": "Manufactured"},
            {"point_order": 2, "location_name": "Yangon International Port", "lat": 16.7808, "lng": 96.1650, "event": "Shipped"},
            {"point_order": 3, "location_name": "Mandalay Distribution Hub", "lat": 21.9731, "lng": 96.0836, "event": "Arrived at Distributor"},
            {"point_order": 4, "location_name": "Mandalay Central Pharmacy", "lat": 21.9588, "lng": 96.0896, "event": "Delivered to Pharmacy"},
        ],
    },
    "BATCH-B": {
        "region": "VIETNAM",
        "mint_date": "2026-06-05",
        "manufacturer": "VinPharm Joint Stock Co.",
        "drug_name": "Amoxicillin 250mg",
        "drug_use": "Antibiotic",
        "expiry": "2028-02",
        "route": [
            {"point_order": 1, "location_name": "VinPharm Factory — Hanoi", "lat": 21.0278, "lng": 105.8342, "event": "Manufactured"},
            {"point_order": 2, "location_name": "Da Nang Logistics Hub", "lat": 16.0544, "lng": 108.2022, "event": "Transit Check"},
            {"point_order": 3, "location_name": "Ho Chi Minh City Warehouse", "lat": 10.8231, "lng": 106.6297, "event": "Arrived at Distributor"},
            {"point_order": 4, "location_name": "Saigon Central Pharmacy", "lat": 10.7769, "lng": 106.7009, "event": "Delivered to Pharmacy"},
        ],
    },
    "BATCH-C": {
        "region": "THAILAND",
        "mint_date": "2026-06-10",
        "manufacturer": "SiamPharm Co., Ltd.",
        "drug_name": "Omeprazole 20mg",
        "drug_use": "Acid Reflux",
        "expiry": "2027-11",
        "route": [
            {"point_order": 1, "location_name": "SiamPharm Factory — Bangkok", "lat": 13.7563, "lng": 100.5018, "event": "Manufactured"},
            {"point_order": 2, "location_name": "Chiang Mai Distribution Center", "lat": 18.7883, "lng": 98.9853, "event": "Arrived at Distributor"},
            {"point_order": 3, "location_name": "Phuket Regional Pharmacy", "lat": 7.8804, "lng": 98.3923, "event": "Delivered to Pharmacy"},
        ],
    },
}


async def seed():
    await init_db()
    db = await get_db()

    for batch_id, data in SUPPLY_CHAIN.items():
        region = data["region"]
        mint_date = data["mint_date"]
        manufacturer = data.get("manufacturer", "")
        drug_name = data.get("drug_name", "")
        drug_use = data.get("drug_use", "")
        expiry = data.get("expiry", "")

        existing = await db.execute_fetchall(
            "SELECT batch_id FROM batches WHERE batch_id = ?", (batch_id,)
        )
        if existing:
            print(f"  Skipping {batch_id} — already exists")
            continue

        await db.execute(
            "INSERT INTO batches (batch_id, region, mint_date, manufacturer, drug_name, drug_use, expiry) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (batch_id, region, mint_date, manufacturer, drug_name, drug_use, expiry),
        )

        for point in data["route"]:
            await db.execute(
                "INSERT INTO route_points (batch_id, point_order, location_name, lat, lng, event) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (batch_id, point["point_order"], point["location_name"],
                 point["lat"], point["lng"], point["event"]),
            )

        print(f"  Seeded {batch_id}: {region}, {len(data['route'])} route points, {drug_name}")

    await db.commit()
    await db.close()
    print("\nDone. Batches seeded: " + ", ".join(SUPPLY_CHAIN.keys()))


if __name__ == "__main__":
    asyncio.run(seed())

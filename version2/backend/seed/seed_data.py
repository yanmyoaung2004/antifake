"""
Seeds the database with batch data and realistic supply chain routes.
Run once: uv run python seed/seed_data.py
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

        existing = await db.execute_fetchall(
            "SELECT batch_id FROM batches WHERE batch_id = ?", (batch_id,)
        )
        if existing:
            print(f"  Skipping {batch_id} — already exists")
            continue

        await db.execute(
            "INSERT INTO batches (batch_id, region, mint_date) VALUES (?, ?, ?)",
            (batch_id, region, mint_date),
        )

        for point in data["route"]:
            await db.execute(
                "INSERT INTO route_points (batch_id, point_order, location_name, lat, lng, event) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (batch_id, point["point_order"], point["location_name"],
                 point["lat"], point["lng"], point["event"]),
            )

        print(f"  Seeded {batch_id}: {region}, {len(data['route'])} route points")

    await db.commit()
    await db.close()
    print("\nDone. Batches seeded: " + ", ".join(SUPPLY_CHAIN.keys()))


if __name__ == "__main__":
    asyncio.run(seed())

import aiosqlite

DB_PATH = "antifake.db"


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY,
            region TEXT NOT NULL,
            mint_date TEXT NOT NULL,
            manufacturer TEXT DEFAULT '',
            drug_name TEXT DEFAULT '',
            drug_use TEXT DEFAULT '',
            expiry TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS route_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            point_order INTEGER NOT NULL,
            location_name TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            event TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        );

        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial TEXT NOT NULL,
            batch_id TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            timestamp TEXT NOT NULL,
            result TEXT NOT NULL,
            scanned_at TEXT DEFAULT (datetime('now')),
            chain_hash TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_scans_serial ON scans(serial);
        CREATE INDEX IF NOT EXISTS idx_route_points_batch ON route_points(batch_id);
    """)
    # Migrations for older DBs
    migrations = [
        "ALTER TABLE batches ADD COLUMN manufacturer TEXT DEFAULT ''",
        "ALTER TABLE batches ADD COLUMN drug_name TEXT DEFAULT ''",
        "ALTER TABLE batches ADD COLUMN drug_use TEXT DEFAULT ''",
        "ALTER TABLE batches ADD COLUMN expiry TEXT DEFAULT ''",
        "ALTER TABLE scans ADD COLUMN chain_hash TEXT DEFAULT ''",
    ]
    for sql in migrations:
        try:
            await db.execute(sql)
        except Exception:
            pass
    await db.commit()
    await db.close()


async def get_batch(batch_id: str) -> dict | None:
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT * FROM batches WHERE batch_id = ?", (batch_id,)
    )
    await db.close()
    if not row:
        return None
    return dict(row[0])


async def upsert_batch(
    batch_id: str,
    region: str,
    mint_date: str,
    manufacturer: str = "",
    drug_name: str = "",
    drug_use: str = "",
    expiry: str = "",
) -> bool:
    """Insert or update a batch. Returns True if a new row was inserted."""
    db = await get_db()
    existing = await db.execute_fetchall(
        "SELECT batch_id FROM batches WHERE batch_id = ?", (batch_id,)
    )
    if existing:
        await db.execute(
            "UPDATE batches SET region=?, mint_date=?, manufacturer=?, drug_name=?, drug_use=?, expiry=? WHERE batch_id=?",
            (region, mint_date, manufacturer, drug_name, drug_use, expiry, batch_id),
        )
        inserted = False
    else:
        await db.execute(
            "INSERT INTO batches (batch_id, region, mint_date, manufacturer, drug_name, drug_use, expiry) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (batch_id, region, mint_date, manufacturer, drug_name, drug_use, expiry),
        )
        inserted = True
    await db.commit()
    await db.close()
    return inserted


async def clear_route(batch_id: str) -> None:
    db = await get_db()
    await db.execute("DELETE FROM route_points WHERE batch_id = ?", (batch_id,))
    await db.commit()
    await db.close()


async def add_route_point(
    batch_id: str,
    point_order: int,
    location_name: str,
    lat: float,
    lng: float,
    event: str,
) -> None:
    db = await get_db()
    await db.execute(
        "INSERT INTO route_points (batch_id, point_order, location_name, lat, lng, event) VALUES (?, ?, ?, ?, ?, ?)",
        (batch_id, point_order, location_name, lat, lng, event),
    )
    await db.commit()
    await db.close()


async def list_batches() -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM batches ORDER BY batch_id"
    )
    await db.close()
    return [dict(r) for r in rows]


async def get_route(batch_id: str) -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM route_points WHERE batch_id = ? ORDER BY point_order",
        (batch_id,),
    )
    await db.close()
    return [dict(r) for r in rows]


async def get_scan_count(serial: str) -> int:
    db = await get_db()
    row = await db.execute_fetchall(
        "SELECT COUNT(*) as c FROM scans WHERE serial = ?", (serial,)
    )
    await db.close()
    return row[0]["c"] if row else 0


async def get_scan_history(serial: str) -> list[dict]:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM scans WHERE serial = ? ORDER BY scanned_at DESC LIMIT 5",
        (serial,),
    )
    await db.close()
    return [dict(r) for r in rows]


async def record_scan(serial: str, batch_id: str, lat: float, lng: float,
                      timestamp: str, result: str):
    db = await get_db()

    last = await db.execute_fetchall(
        "SELECT chain_hash FROM scans WHERE serial = ? ORDER BY id DESC LIMIT 1",
        (serial,),
    )
    prev_hash = last[0]["chain_hash"] if last else "0" * 64

    import hashlib
    raw = f"{serial}|{batch_id}|{lat}|{lng}|{timestamp}|{result}|{prev_hash}"
    chain_hash = hashlib.sha256(raw.encode()).hexdigest()

    await db.execute(
        "INSERT INTO scans (serial, batch_id, lat, lng, timestamp, result, chain_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (serial, batch_id, lat, lng, timestamp, result, chain_hash),
    )
    await db.commit()
    await db.close()


async def verify_chain(serial: str) -> dict:
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT * FROM scans WHERE serial = ? AND chain_hash != '' ORDER BY id ASC",
        (serial,),
    )
    await db.close()
    if not rows:
        return {"intact": True, "total": 0, "message": "No scans to verify"}

    prev = "0" * 64
    for i, row in enumerate(rows):
        import hashlib
        raw = f"{row['serial']}|{row['batch_id']}|{row['lat']}|{row['lng']}|{row['timestamp']}|{row['result']}|{prev}"
        computed = hashlib.sha256(raw.encode()).hexdigest()
        if computed != row["chain_hash"]:
            return {
                "intact": False,
                "total": len(rows),
                "broken_at": i + 1,
                "message": f"Chain broken at record {i + 1}. Data has been tampered with.",
            }
        prev = computed

    return {
        "intact": True,
        "total": len(rows),
        "message": f"Chain intact — {len(rows)} records verified.",
    }

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
            mint_date TEXT NOT NULL
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
            scanned_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_scans_serial ON scans(serial);
        CREATE INDEX IF NOT EXISTS idx_route_points_batch ON route_points(batch_id);
    """)
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
    await db.execute(
        "INSERT INTO scans (serial, batch_id, lat, lng, timestamp, result) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (serial, batch_id, lat, lng, timestamp, result),
    )
    await db.commit()
    await db.close()

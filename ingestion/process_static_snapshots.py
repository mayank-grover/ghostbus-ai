import subprocess
import sqlite3
import shutil
from pathlib import Path

DB_PATH = "data/ghostbus.db"
ARCHIVE_DIR = Path("data/koda_static_archive")
EXTRACT_ROOT = Path("data/koda_static_extracted")

DATES = [
    "2026-08-13", "2026-08-14", "2026-08-16", "2026-08-17", "2026-08-18", "2026-08-19",
    "2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23", "2026-08-24", "2026-08-25"
]

def init_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS static_snapshot_calendar (
        snapshot_date TEXT, service_id TEXT,
        monday INTEGER, tuesday INTEGER, wednesday INTEGER, thursday INTEGER,
        friday INTEGER, saturday INTEGER, sunday INTEGER,
        start_date TEXT, end_date TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS static_snapshot_calendar_dates (
        snapshot_date TEXT, service_id TEXT, date TEXT, exception_type INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS static_snapshot_trips (
        snapshot_date TEXT, route_id TEXT, service_id TEXT, trip_id TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS static_snapshot_stop_times (
        snapshot_date TEXT, trip_id TEXT, arrival_time TEXT, departure_time TEXT,
        stop_id TEXT, stop_sequence INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS processed_static_snapshots (
        snapshot_date TEXT PRIMARY KEY
    )""")
    conn.commit()

def already_done(conn, date):
    return conn.execute(
        "SELECT 1 FROM processed_static_snapshots WHERE snapshot_date = ?", (date,)
    ).fetchone() is not None

def process_date(conn, date):
    if already_done(conn, date):
        print(f"{date}: already processed, skipping")
        return

    archive_path = ARCHIVE_DIR / f"static_{date}.7z"
    extract_path = EXTRACT_ROOT / date
    extract_path.mkdir(parents=True, exist_ok=True)

    print(f"{date}: extracting")
    subprocess.run(["7zz", "x", str(archive_path), f"-o{extract_path}", "-y"], check=True)

    print(f"{date}: importing calendar")
    with open(extract_path / "calendar.txt") as f:
        next(f)
        rows = []
        for line in f:
            parts = line.strip().split(",")
            rows.append((date, *parts))
        conn.executemany(
            "INSERT INTO static_snapshot_calendar VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
        )

    print(f"{date}: importing calendar_dates")
    with open(extract_path / "calendar_dates.txt") as f:
        next(f)
        rows = [(date, *line.strip().split(",")) for line in f]
        conn.executemany(
            "INSERT INTO static_snapshot_calendar_dates VALUES (?,?,?,?)", rows
        )

    print(f"{date}: importing trips (route_id, service_id, trip_id only)")
    with open(extract_path / "trips.txt") as f:
        header = next(f).strip().split(",")
        idx = {name: i for i, name in enumerate(header)}
        rows = []
        for line in f:
            parts = line.strip().split(",")
            rows.append((date, parts[idx["route_id"]], parts[idx["service_id"]], parts[idx["trip_id"]]))
        conn.executemany(
            "INSERT INTO static_snapshot_trips VALUES (?,?,?,?)", rows
        )

    print(f"{date}: importing stop_times (trip_id, times, stop_id, stop_sequence only) - this is the big one")
    with open(extract_path / "stop_times.txt") as f:
        header = next(f).strip().split(",")
        idx = {name: i for i, name in enumerate(header)}
        batch = []
        count = 0
        for line in f:
            parts = line.strip().split(",")
            batch.append((
                date, parts[idx["trip_id"]], parts[idx["arrival_time"]],
                parts[idx["departure_time"]], parts[idx["stop_id"]], parts[idx["stop_sequence"]]
            ))
            if len(batch) >= 10000:
                conn.executemany(
                    "INSERT INTO static_snapshot_stop_times VALUES (?,?,?,?,?,?)", batch
                )
                count += len(batch)
                batch = []
        if batch:
            conn.executemany(
                "INSERT INTO static_snapshot_stop_times VALUES (?,?,?,?,?,?)", batch
            )
            count += len(batch)
        print(f"{date}: inserted {count} stop_times rows")

    conn.commit()
    conn.execute("INSERT INTO processed_static_snapshots VALUES (?)", (date,))
    conn.commit()

    print(f"{date}: deleting extracted files to free disk")
    shutil.rmtree(extract_path)

def main():
    conn = sqlite3.connect(DB_PATH)
    init_tables(conn)
    for date in DATES:
        process_date(conn, date)
    conn.close()
    print("All static snapshots processed.")

if __name__ == "__main__":
    main()

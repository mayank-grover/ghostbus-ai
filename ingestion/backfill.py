import sqlite3
import shutil
from pathlib import Path

from parser import parse_gtfsrt_file


DB_PATH = "../data/ghostbus.db"
EXTRACTED_ROOT = Path("../data/koda_extracted")


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_observations (
            trip_id TEXT,
            route_id TEXT,
            stop_id TEXT,
            service_date TEXT,
            scheduled_time INTEGER,
            predicted_time INTEGER,
            delay_seconds INTEGER,
            schedule_relationship INTEGER,
            polled_at INTEGER,
            source TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_dates (
            date TEXT PRIMARY KEY
        )
    """)

    conn.commit()


def already_processed(conn, date):
    cur = conn.execute(
        "SELECT 1 FROM processed_dates WHERE date = ?",
        (date,)
    )
    return cur.fetchone() is not None


def mark_processed(conn, date):
    conn.execute(
        "INSERT OR IGNORE INTO processed_dates (date) VALUES (?)",
        (date,)
    )
    conn.commit()


def flush(conn, batch):
    conn.executemany("""
        INSERT INTO raw_observations (
            trip_id,
            route_id,
            stop_id,
            service_date,
            scheduled_time,
            predicted_time,
            delay_seconds,
            schedule_relationship,
            polled_at,
            source
        )
        VALUES (
            :trip_id,
            :route_id,
            :stop_id,
            :service_date,
            :scheduled_time,
            :predicted_time,
            :delay_seconds,
            :schedule_relationship,
            :polled_at,
            :source
        )
    """, batch)

    conn.commit()


def process_date_folder(conn, date_folder):
    date = date_folder.name.replace("tripupdates_", "")

    if already_processed(conn, date):
        print(f"Already processed {date}, skipping")
        return

    pb_files = list(date_folder.rglob("*.pb"))

    print(f"\nProcessing {date}: {len(pb_files)} files")

    batch = []

    for i, pb_file in enumerate(pb_files, start=1):
        try:
            rows = parse_gtfsrt_file(str(pb_file))
            batch.extend(rows)

        except Exception as e:
            print(f"Skipping {pb_file.name}: {e}")
            continue

        if len(batch) >= 5000:
            flush(conn, batch)
            batch = []

        if i % 500 == 0:
            print(f"  {i}/{len(pb_files)} files parsed")

    if batch:
        flush(conn, batch)

    mark_processed(conn, date)

    print(f"Finished {date}")
    print(f"Deleting {date_folder}")

    shutil.rmtree(date_folder)


def main():
    conn = sqlite3.connect(DB_PATH)

    init_db(conn)

    date_folders = sorted(
        d for d in EXTRACTED_ROOT.iterdir()
        if d.is_dir()
    )

    for date_folder in date_folders:
        process_date_folder(conn, date_folder)

    conn.close()

    print("\nBackfill complete.")


if __name__ == "__main__":
    main()

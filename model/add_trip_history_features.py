import sqlite3

DB_PATH = "data/ghostbus.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_labeled_v2_trip_seq
        ON labeled_stops_v2_final(service_date, trip_id, stop_sequence)
    """)
    conn.commit()

    rows = conn.execute("""
        SELECT rowid, service_date, trip_id, stop_sequence, is_skip, delay_seconds
        FROM labeled_stops_v2_final
        ORDER BY service_date, trip_id, stop_sequence
    """).fetchall()

    print(f"Loaded {len(rows)} rows for sequential feature build")

    conn.execute("ALTER TABLE labeled_stops_v2_final ADD COLUMN prior_skips_this_trip INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE labeled_stops_v2_final ADD COLUMN last_known_delay INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE labeled_stops_v2_final ADD COLUMN has_known_delay INTEGER DEFAULT 0")

    updates = []
    current_key = None
    running_skips = 0
    last_delay = 0
    has_delay = 0

    for rowid, service_date, trip_id, stop_sequence, is_skip, delay_seconds in rows:
        key = (service_date, trip_id)
        if key != current_key:
            current_key = key
            running_skips = 0
            last_delay = 0
            has_delay = 0

        updates.append((running_skips, last_delay, has_delay, rowid))

        running_skips += is_skip
        if delay_seconds is not None:
            last_delay = delay_seconds
            has_delay = 1

    print(f"Computed features for {len(updates)} rows, writing back...")

    conn.executemany("""
        UPDATE labeled_stops_v2_final
        SET prior_skips_this_trip = ?, last_known_delay = ?, has_known_delay = ?
        WHERE rowid = ?
    """, updates)
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()

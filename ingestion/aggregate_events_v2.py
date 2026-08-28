import sqlite3

DB_PATH = "data/ghostbus.db"

conn = sqlite3.connect(DB_PATH)

conn.execute("DROP TABLE IF EXISTS stop_events_v2")

conn.execute("""
CREATE TABLE stop_events_v2 (
    trip_id TEXT,
    stop_id TEXT,
    route_id TEXT,
    service_date TEXT,
    last_polled_at INTEGER,
    predicted_time INTEGER,
    delay_seconds INTEGER,
    schedule_relationship INTEGER
)
""")

dates = [
    row[0]
    for row in conn.execute("""
        SELECT DISTINCT service_date
        FROM raw_observations
        ORDER BY service_date
    """)
]

print("Dates:", dates)

for date in dates:
    print(f"\nProcessing {date}...")

    conn.execute("""
        INSERT INTO stop_events_v2
        SELECT
            r.trip_id,
            r.stop_id,
            r.route_id,
            r.service_date,
            r.polled_at,
            r.predicted_time,
            r.delay_seconds,
            r.schedule_relationship
        FROM raw_observations r
        WHERE r.service_date = ?
        AND r.rowid = (
            SELECT r2.rowid
            FROM raw_observations r2
            WHERE r2.trip_id = r.trip_id
              AND r2.stop_id = r.stop_id
              AND r2.service_date = r.service_date
            ORDER BY r2.polled_at DESC, r2.rowid DESC
            LIMIT 1
        )
    """, (date,))

    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM stop_events_v2 WHERE service_date = ?",
        (date,)
    ).fetchone()[0]

    print(f"Finished {date}: {count} unique stops")

conn.execute("""
CREATE INDEX idx_stop_events_v2_trip_stop_date
ON stop_events_v2(trip_id, stop_id, service_date)
""")

conn.commit()
conn.close()

print("\nAggregation complete.")

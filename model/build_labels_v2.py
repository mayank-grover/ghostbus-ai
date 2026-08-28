import sqlite3

DB_PATH = "data/ghostbus.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS labeled_stops_v2")
    conn.execute("""
        CREATE TABLE labeled_stops_v2 AS
        SELECT
            service_date, trip_id, route_id, stop_id,
            last_polled_at, predicted_time, delay_seconds,
            schedule_relationship AS is_skip
        FROM stop_events_v2
    """)
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2").fetchone()[0]
    skips = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2 WHERE is_skip = 1").fetchone()[0]
    print(f"Total: {total}, Skips: {skips}, Rate: {100*skips/total:.4f}%")

    conn.close()

if __name__ == "__main__":
    main()

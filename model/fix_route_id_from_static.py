import sqlite3

DB_PATH = "data/ghostbus.db"

def main():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("ALTER TABLE labeled_stops_v2_final ADD COLUMN route_id_fixed TEXT")

    conn.execute("""
        UPDATE labeled_stops_v2_final
        SET route_id_fixed = (
            SELECT t.route_id
            FROM static_snapshot_trips t
            WHERE t.snapshot_date = labeled_stops_v2_final.snapshot_date
            AND t.trip_id = labeled_stops_v2_final.trip_id
            LIMIT 1
        )
    """)
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2_final").fetchone()[0]
    missing = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2_final WHERE route_id_fixed IS NULL").fetchone()[0]
    print(f"Total: {total}, Missing route_id after static join: {missing} ({100*missing/total:.2f}%)")

    conn.close()

if __name__ == "__main__":
    main()

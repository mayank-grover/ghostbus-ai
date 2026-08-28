import sqlite3

DB_PATH = "data/ghostbus.db"

def to_dashed(date_nodash: str) -> str:
    return f"{date_nodash[0:4]}-{date_nodash[4:6]}-{date_nodash[6:8]}"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("ALTER TABLE labeled_stops_v2 ADD COLUMN snapshot_date TEXT")
    conn.execute("""
        UPDATE labeled_stops_v2
        SET snapshot_date = substr(service_date,1,4)||'-'||substr(service_date,5,2)||'-'||substr(service_date,7,2)
    """)
    conn.commit()

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_labeled_v2_join
        ON labeled_stops_v2(snapshot_date, trip_id, stop_id)
    """)

    conn.execute("DROP TABLE IF EXISTS labeled_stops_v2_final")
    conn.execute("""
        CREATE TABLE labeled_stops_v2_final AS
        SELECT l.*, st.stop_sequence
        FROM labeled_stops_v2 l
        LEFT JOIN static_snapshot_stop_times st
            ON st.snapshot_date = l.snapshot_date
            AND st.trip_id = l.trip_id
            AND st.stop_id = l.stop_id
    """)
    conn.commit()

    missing = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2_final WHERE stop_sequence IS NULL").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM labeled_stops_v2_final").fetchone()[0]
    print(f"Total: {total}, Missing stop_sequence: {missing} ({100*missing/total:.2f}%)")

    conn.close()

if __name__ == "__main__":
    main()

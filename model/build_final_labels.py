import sqlite3
from datetime import datetime
from config import VALID_SERVICE_DATES

DB_PATH = "data/ghostbus.db"
DOW_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def to_dashed(date_nodash: str) -> str:
    return f"{date_nodash[0:4]}-{date_nodash[4:6]}-{date_nodash[6:8]}"

def services_running(conn, snapshot_dashed: str, date_nodash: str) -> set:
    dow_idx = datetime.strptime(date_nodash, "%Y%m%d").weekday()
    dow_col = DOW_COLUMNS[dow_idx]

    base = conn.execute(f"""
        SELECT service_id FROM static_snapshot_calendar
        WHERE snapshot_date = ? AND {dow_col} = 1
        AND start_date <= ? AND end_date >= ?
    """, (snapshot_dashed, date_nodash, date_nodash)).fetchall()
    service_ids = {r[0] for r in base}

    added = conn.execute("""
        SELECT service_id FROM static_snapshot_calendar_dates
        WHERE snapshot_date = ? AND date = ? AND exception_type = 1
    """, (snapshot_dashed, date_nodash)).fetchall()
    service_ids |= {r[0] for r in added}

    removed = conn.execute("""
        SELECT service_id FROM static_snapshot_calendar_dates
        WHERE snapshot_date = ? AND date = ? AND exception_type = 2
    """, (snapshot_dashed, date_nodash)).fetchall()
    service_ids -= {r[0] for r in removed}

    return service_ids

def build_labels():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS labeled_stops")
    conn.execute("""
        CREATE TABLE labeled_stops (
            service_date TEXT, trip_id TEXT, route_id TEXT, stop_id TEXT,
            stop_sequence INTEGER, scheduled_arrival_time TEXT, scheduled_departure_time TEXT,
            observed INTEGER, delay_seconds INTEGER, predicted_time INTEGER
        )
    """)
    conn.commit()

    for date_nodash in VALID_SERVICE_DATES:
        dashed = to_dashed(date_nodash)
        print(f"Processing {date_nodash}...")

        running = services_running(conn, dashed, date_nodash)
        print(f"  {len(running)} services running")
        if not running:
            print(f"  WARNING: 0 services for {date_nodash}, skipping this date entirely")
            continue

        conn.execute("DROP TABLE IF EXISTS temp_running_services")
        conn.execute("CREATE TEMP TABLE temp_running_services (service_id TEXT)")
        conn.executemany(
            "INSERT INTO temp_running_services VALUES (?)",
            [(s,) for s in running]
        )

        conn.execute("""
            INSERT INTO labeled_stops
            SELECT
                ? AS service_date,
                st.trip_id,
                tr.route_id,
                st.stop_id,
                st.stop_sequence,
                st.arrival_time,
                st.departure_time,
                CASE WHEN se.trip_id IS NOT NULL THEN 1 ELSE 0 END AS observed,
                se.delay_seconds,
                se.predicted_time
            FROM static_snapshot_stop_times st
            JOIN static_snapshot_trips tr
                ON tr.snapshot_date = st.snapshot_date AND tr.trip_id = st.trip_id
            JOIN temp_running_services rs ON rs.service_id = tr.service_id
            LEFT JOIN stop_events se
                ON se.trip_id = st.trip_id
                AND se.stop_id = st.stop_id
                AND se.service_date = ?
            WHERE st.snapshot_date = ?
        """, (date_nodash, date_nodash, dashed))
        conn.commit()

        count = conn.execute(
            "SELECT COUNT(*) FROM labeled_stops WHERE service_date = ?", (date_nodash,)
        ).fetchone()[0]
        skipped = conn.execute(
            "SELECT COUNT(*) FROM labeled_stops WHERE service_date = ? AND observed = 0", (date_nodash,)
        ).fetchone()[0]
        print(f"  {count} labeled rows, {skipped} marked skipped ({100*skipped/count:.1f}%)")

    conn.close()
    print("Done.")

if __name__ == "__main__":
    build_labels()

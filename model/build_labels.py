import sqlite3
from datetime import datetime
from config import VALID_SERVICE_DATES

DB_PATH = "data/ghostbus.db"
DOW_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

def services_running_on(conn, date_str: str) -> set:
    dow_index = datetime.strptime(date_str, "%Y%m%d").weekday()
    dow_col = DOW_COLUMNS[dow_index]

    base = conn.execute(f"""
        SELECT service_id FROM gtfs_calendar
        WHERE {dow_col} = 1 AND start_date <= ? AND end_date >= ?
    """, (date_str, date_str)).fetchall()
    service_ids = {row[0] for row in base}

    added = conn.execute("""
        SELECT service_id FROM gtfs_calendar_dates
        WHERE date = ? AND exception_type = 1
    """, (date_str,)).fetchall()
    service_ids |= {row[0] for row in added}

    removed = conn.execute("""
        SELECT service_id FROM gtfs_calendar_dates
        WHERE date = ? AND exception_type = 2
    """, (date_str,)).fetchall()
    service_ids -= {row[0] for row in removed}

    return service_ids

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    for date in VALID_SERVICE_DATES:
        svc_ids = services_running_on(conn, date)
        print(f"{date}: {len(svc_ids)} services running")
    conn.close()

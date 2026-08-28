import sqlite3
import pandas as pd
import json

DB_PATH = "data/ghostbus.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM labeled_stops_v2_final", conn)
    conn.close()

    df['hour'] = pd.to_datetime(df['last_polled_at'], unit='s', utc=True).dt.hour

    # Use ALL 12 days for these lookups (not train-only) since this is now
    # the final, frozen reference table for live serving — not test evaluation.
    # No leakage concern here: there's no more "test set" once we're serving live.
    route_stats = df.groupby('route_id')['is_skip'].agg(['mean', 'count']).reset_index()
    route_stats.columns = ['route_id', 'route_skip_rate', 'route_count']

    stop_stats = df.groupby('stop_id')['is_skip'].agg(['mean', 'count']).reset_index()
    stop_stats.columns = ['stop_id', 'stop_skip_rate', 'stop_count']

    route_hour_stats = df.groupby(['route_id', 'hour'])['is_skip'].agg(['mean', 'count']).reset_index()
    route_hour_stats.columns = ['route_id', 'hour', 'route_hour_skip_rate', 'route_hour_count']

    # Global fallback for unseen route/stop combos (new routes, sparse data)
    global_skip_rate = df['is_skip'].mean()

    route_stats.to_csv("model/lookup_route_stats.csv", index=False)
    stop_stats.to_csv("model/lookup_stop_stats.csv", index=False)
    route_hour_stats.to_csv("model/lookup_route_hour_stats.csv", index=False)

    with open("model/lookup_metadata.json", "w") as f:
        json.dump({
            "global_skip_rate": global_skip_rate,
            "n_routes": len(route_stats),
            "n_stops": len(stop_stats),
            "n_route_hour_combos": len(route_hour_stats),
            "training_dates": sorted(df['service_date'].astype(str).unique().tolist())
        }, f, indent=2)

    print(f"Routes: {len(route_stats)}, Stops: {len(stop_stats)}, Route-hour combos: {len(route_hour_stats)}")
    print(f"Global skip rate (fallback): {global_skip_rate:.6f}")
    print("Saved: lookup_route_stats.csv, lookup_stop_stats.csv, lookup_route_hour_stats.csv, lookup_metadata.json")

if __name__ == "__main__":
    main()

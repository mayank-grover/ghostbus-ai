"""
Static GTFS lookup utilities for GhostBus AI.

Maps live GTFS-RT trip IDs to route IDs and provides ordered stop
and route metadata from the static GTFS feed.
"""

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

GTFS_DIR = PROJECT_ROOT / "data" / "gtfs_static"

TRIPS_FILE = GTFS_DIR / "trips.txt"
STOP_TIMES_FILE = GTFS_DIR / "stop_times.txt"
STOPS_FILE = GTFS_DIR / "stops.txt"
ROUTES_FILE = GTFS_DIR / "routes.txt"


class GTFSLookup:

    def __init__(self):
        self.trip_to_route = {}
        self.trip_stops = {}
        self.stop_metadata = {}
        self.route_metadata = {}

        self._load_trips()
        self._load_stop_times()
        self._load_stops()
        self._load_routes()

    def _load_trips(self):
        with open(TRIPS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.trip_to_route[row["trip_id"]] = row["route_id"]

    def _load_stop_times(self):
        with open(STOP_TIMES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                trip_id = row["trip_id"]

                self.trip_stops.setdefault(trip_id, []).append(
                    {
                        "stop_id": row["stop_id"],
                        "stop_sequence": int(row["stop_sequence"]),
                    }
                )

        for stops in self.trip_stops.values():
            stops.sort(key=lambda x: x["stop_sequence"])

    def _load_stops(self):
        with open(STOPS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.stop_metadata[row["stop_id"]] = {
                    "stop_id": row["stop_id"],
                    "stop_name": row["stop_name"],
                    "latitude": float(row["stop_lat"]),
                    "longitude": float(row["stop_lon"]),
                }

    def _load_routes(self):
        with open(ROUTES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                self.route_metadata[row["route_id"]] = {
                    "route_id": row["route_id"],
                    "route_short_name": row["route_short_name"],
                    "route_long_name": row["route_long_name"],
                    "route_type": row["route_type"],
                }

    def get_route_id(self, trip_id: str):
        return self.trip_to_route.get(trip_id)

    def get_stops(self, trip_id: str):
        return self.trip_stops.get(trip_id, [])

    def get_stop_metadata(self, stop_id: str):
        return self.stop_metadata.get(stop_id)

    def search_stops(self, query: str, limit: int = 20):
        query = query.strip().lower()

        if not query:
            return []

        matches = []

        for stop in self.stop_metadata.values():
            if query in stop["stop_name"].lower():
                matches.append(stop)

                if len(matches) >= limit:
                    break

        return matches

    def get_route_metadata(self, route_id: str):
        return self.route_metadata.get(route_id)


_lookup = None


def get_gtfs_lookup():
    global _lookup

    if _lookup is None:
        _lookup = GTFSLookup()

    return _lookup

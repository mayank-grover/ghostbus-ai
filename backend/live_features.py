"""
Live feature extraction for GhostBus AI.

Converts GTFS-RT TripUpdates into the live features
required by the skip prediction model.
"""

from backend.gtfs_lookup import get_gtfs_lookup
from google.transit import gtfs_realtime_pb2


def extract_trip_features(trip_update):
    """
    Extract model-ready context from one GTFS-RT TripUpdate.

    Returns one dictionary per stop in the live update.
    """

    lookup = get_gtfs_lookup()

    trip_id = trip_update.trip.trip_id
    route_id = lookup.get_route_id(trip_id)

    if route_id is None:
        return []

    scheduled_stops = lookup.get_stops(trip_id)

    if not scheduled_stops:
        return []

    scheduled_by_sequence = {
        stop["stop_sequence"]: stop
        for stop in scheduled_stops
    }

    total_stops = len(scheduled_stops)
    results = []

    prior_skips = 0

    updates = sorted(
        trip_update.stop_time_update,
        key=lambda update: update.stop_sequence,
    )

    for update in updates:

        stop_id = update.stop_id
        stop_sequence = update.stop_sequence

        if stop_sequence not in scheduled_by_sequence:
            continue

        stops_remaining = sum(
            1
            for stop in scheduled_stops
            if stop["stop_sequence"] > stop_sequence
        )

        # Match training semantics:
        # use the latest known delay before this stop.
        delay = 0.0
        has_known_delay = 0

        if update.HasField("arrival") and update.arrival.HasField("delay"):
            delay = float(update.arrival.delay)
            has_known_delay = 1

        elif update.HasField("departure") and update.departure.HasField("delay"):
            delay = float(update.departure.delay)
            has_known_delay = 1

        results.append(
            {
                "trip_id": trip_id,
                "route_id": route_id,
                "stop_id": stop_id,
                "stop_sequence": stop_sequence,
                "prior_skips_this_trip": prior_skips,
                "last_known_delay": delay,
                "has_known_delay": has_known_delay,
                "stops_remaining": stops_remaining,
            }
        )

        # GTFS-RT schedule_relationship:
        # SKIPPED = 1
        if (
            update.HasField("schedule_relationship")
            and update.schedule_relationship
            == gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.SKIPPED
        ):
            prior_skips += 1

    return results

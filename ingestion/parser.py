from google.transit import gtfs_realtime_pb2


def parse_gtfsrt_file(filepath: str) -> list[dict]:
    feed = gtfs_realtime_pb2.FeedMessage()

    with open(filepath, "rb") as f:
        feed.ParseFromString(f.read())

    rows = []
    feed_timestamp = feed.header.timestamp

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update
        trip_id = tu.trip.trip_id
        route_id = tu.trip.route_id

        for stu in tu.stop_time_update:
            predicted_time = None
            delay_seconds = None

            if stu.HasField("arrival"):
                predicted_time = stu.arrival.time
                delay_seconds = stu.arrival.delay
            elif stu.HasField("departure"):
                predicted_time = stu.departure.time
                delay_seconds = stu.departure.delay

            rows.append({
                "trip_id": trip_id,
                "route_id": route_id,
                "stop_id": stu.stop_id,
                "scheduled_time": None,
                "predicted_time": predicted_time,
                "delay_seconds": delay_seconds,
                "polled_at": feed_timestamp,
                "source": "koda_archive",
            })

    return rows

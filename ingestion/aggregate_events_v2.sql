DROP TABLE IF EXISTS stop_events_v2;

CREATE TABLE stop_events_v2 AS
SELECT
    trip_id,
    stop_id,
    route_id,
    service_date,
    polled_at AS last_polled_at,
    predicted_time,
    delay_seconds,
    schedule_relationship
FROM (
    SELECT
        rowid,
        trip_id,
        stop_id,
        route_id,
        service_date,
        polled_at,
        predicted_time,
        delay_seconds,
        schedule_relationship,
        ROW_NUMBER() OVER (
            PARTITION BY trip_id, stop_id, service_date
            ORDER BY polled_at DESC, rowid DESC
        ) AS rn
    FROM raw_observations
)
WHERE rn = 1;

CREATE INDEX idx_stop_events_v2_trip_stop_date
ON stop_events_v2(trip_id, stop_id, service_date);

CREATE INDEX idx_stop_events_v2_route
ON stop_events_v2(route_id);

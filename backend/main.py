from pathlib import Path
"""
GhostBus AI - FastAPI Backend Service

This module serves as the primary REST API backend for GhostBus AI,
providing endpoints for system health, GTFS real-time data ingestion status,
stop predictions, and ghost bus alerts.
"""

import logging
import csv
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from backend.predictor import get_predictor
from backend.live_data import fetch_trip_updates
from backend.live_features import extract_trip_features
from backend.gtfs_lookup import get_gtfs_lookup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostbus-backend")

STOPS_INDEX = []

LIVE_ACTIVITY_CACHE = {
    "data": None,
    "computed_at": None,
}

LIVE_ACTIVITY_REFRESH_SECONDS = 20

app = FastAPI(
    title="GhostBus AI API",
    description="Backend API for GhostBus AI transit monitoring and arrival predictions.",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def refresh_live_activity_cache():
    """Fetch, predict, aggregate, and cache live activity data."""
    try:
        feed = await fetch_trip_updates()
        predictor = get_predictor()
        gtfs_lookup = get_gtfs_lookup()

        all_features = []

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue

            features_list = extract_trip_features(entity.trip_update)
            all_features.extend(features_list)

        logger.info(
            "Live activity refresh: extracted %d stop features",
            len(all_features),
        )

        results = predictor.predict_batch(all_features)

        stop_predictions = {}

        for feature, result in zip(all_features, results):
            stop_id = feature["stop_id"]

            if stop_id not in stop_predictions:
                stop_predictions[stop_id] = []

            stop_predictions[stop_id].append({
                "trip_id": feature["trip_id"],
                "route_id": feature["route_id"],
                "skip_probability": result["skip_probability"],
                "high_confidence_alert": result["high_confidence_alert"],
            })

        stops_summary = []

        for stop_id, trips in stop_predictions.items():
            stop_metadata = gtfs_lookup.get_stop_metadata(stop_id)

            stop_name = (
                stop_metadata["stop_name"]
                if stop_metadata
                else "Unknown stop"
            )

            highest_probability = max(
                trip["skip_probability"]
                for trip in trips
            )

            high_confidence = any(
                trip["high_confidence_alert"]
                for trip in trips
            )

            stops_summary.append({
                "stop_id": stop_id,
                "stop_name": stop_name,
                "latitude": (
                    stop_metadata["latitude"]
                    if stop_metadata
                    else None
                ),
                "longitude": (
                    stop_metadata["longitude"]
                    if stop_metadata
                    else None
                ),
                "prediction_count": len(trips),
                "highest_skip_probability": highest_probability,
                "high_confidence_alert": high_confidence,
                "trips": trips,
            })

        stops_summary.sort(
            key=lambda stop: stop["highest_skip_probability"],
            reverse=True,
        )

        LIVE_ACTIVITY_CACHE["data"] = {
            "prediction_count": len(all_features),
            "stop_count": len(stops_summary),
            "stops": stops_summary,
        }

        LIVE_ACTIVITY_CACHE["computed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Live activity cache refreshed: %d predictions, %d stops",
            len(all_features),
            len(stops_summary),
        )

    except Exception:
        logger.exception("Live activity cache refresh failed")


async def live_activity_worker():
    """Continuously refresh live activity in the background."""
    while True:
        await refresh_live_activity_cache()
        await asyncio.sleep(LIVE_ACTIVITY_REFRESH_SECONDS)


@app.on_event("startup")
async def load_model():
    global STOPS_INDEX

    logger.info("Loading skip prediction model...")
    get_predictor()
    logger.info("Model loaded successfully.")

    stops_file = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "gtfs_static"
        / "stops.txt"
    )

    logger.info("Loading stop search index...")

    with open(stops_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        STOPS_INDEX = [
            {
                "stop_id": row["stop_id"],
                "stop_name": row["stop_name"],
                "latitude": float(row["stop_lat"]),
                "longitude": float(row["stop_lon"]),
            }
            for row in reader
        ]

    logger.info(f"Loaded {len(STOPS_INDEX)} stops into search index.")

    # Start background live-activity refresh worker.
    asyncio.create_task(live_activity_worker())
    logger.info(
        "Live activity background worker started "
        "(refresh every %ds)",
        LIVE_ACTIVITY_REFRESH_SECONDS,
    )


@app.get("/health", tags=["Health"])
async def health_check():
    logger.info("Health check endpoint pinged.")
    return {
        "status": "ok",
        "service": "ghostbus-ai-backend",
        "version": "0.2.0"
    }


class PredictionRequest(BaseModel):
    route_id: str
    stop_id: str
    prior_skips_this_trip: int = 0
    last_known_delay: float = 0.0
    has_known_delay: int = 0
    stops_remaining: int = 0


class PredictionResponse(BaseModel):
    skip_probability: float
    high_confidence_alert: bool
    features_used: dict


@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict_skip(request: PredictionRequest):
    try:
        predictor = get_predictor()
        result = predictor.predict(
            route_id=request.route_id,
            stop_id=request.stop_id,
            prior_skips_this_trip=request.prior_skips_this_trip,
            last_known_delay=request.last_known_delay,
            has_known_delay=request.has_known_delay,
            stops_remaining=request.stops_remaining,
            current_time=datetime.now(timezone.utc),
        )
        return result
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# TODO: Add API router for GTFS real-time transit data ingestion (/api/v1/ingestion)
# TODO: Add API router for bus stop lookup and route schedules (/api/v1/stops)
# TODO: Initialize database session management for storing user stop subscriptions
# TODO: Wire live GTFS-RT poller to compute prior_skips_this_trip / last_known_delay
#       automatically instead of requiring caller to supply them

@app.get("/api/v1/live-predictions", tags=["Live Prediction"])
async def get_live_predictions():
    """
    Fetch current SL GTFS-RT data and return skip predictions
    for all stops present in active trip updates.
    """

    try:
        feed = await fetch_trip_updates()
        predictor = get_predictor()

        predictions = []

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue

            features_list = extract_trip_features(entity.trip_update)

            for feature in features_list:
                result = predictor.predict(
                    route_id=feature["route_id"],
                    stop_id=feature["stop_id"],
                    prior_skips_this_trip=feature["prior_skips_this_trip"],
                    last_known_delay=feature["last_known_delay"],
                    has_known_delay=feature["has_known_delay"],
                    stops_remaining=feature["stops_remaining"],
                )

                predictions.append({
                    "trip_id": feature["trip_id"],
                    "route_id": feature["route_id"],
                    "stop_id": feature["stop_id"],
                    "stop_sequence": feature["stop_sequence"],
                    "live_features": {
                        "prior_skips_this_trip": feature["prior_skips_this_trip"],
                        "last_known_delay": feature["last_known_delay"],
                        "has_known_delay": feature["has_known_delay"],
                        "stops_remaining": feature["stops_remaining"],
                    },
                    **result,
                })

        return {
            "prediction_count": len(predictions),
            "predictions": predictions,
        }

    except Exception as e:
        logger.exception("Live prediction failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/live-predictions/{stop_id}", tags=["Live Prediction"])
async def get_stop_live_predictions(stop_id: str):
    """
    Return live skip predictions only for a specific stop.
    """

    try:
        feed = await fetch_trip_updates()
        predictor = get_predictor()

        predictions = []

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue

            features_list = extract_trip_features(entity.trip_update)

            for feature in features_list:
                if feature["stop_id"] != stop_id:
                    continue

                result = predictor.predict(
                    route_id=feature["route_id"],
                    stop_id=feature["stop_id"],
                    prior_skips_this_trip=feature["prior_skips_this_trip"],
                    last_known_delay=feature["last_known_delay"],
                    has_known_delay=feature["has_known_delay"],
                    stops_remaining=feature["stops_remaining"],
                )

                predictions.append({
                    "trip_id": feature["trip_id"],
                    "route_id": feature["route_id"],
                    "stop_id": feature["stop_id"],
                    "stop_sequence": feature["stop_sequence"],
                    "live_features": {
                        "prior_skips_this_trip": feature["prior_skips_this_trip"],
                        "last_known_delay": feature["last_known_delay"],
                        "has_known_delay": feature["has_known_delay"],
                        "stops_remaining": feature["stops_remaining"],
                    },
                    **result,
                })

        stop_metadata = get_gtfs_lookup().get_stop_metadata(stop_id)

        if stop_metadata is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stop {stop_id} not found in static GTFS data",
            )

        return {
            **stop_metadata,
            "prediction_count": len(predictions),
            "predictions": predictions,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Targeted live prediction failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stops/{stop_id}/risk", tags=["Stop Risk"])
async def get_stop_risk(stop_id: str):
    """
    Return a clean, user-facing live skip-risk summary for a stop.
    """

    try:
        stop_metadata = get_gtfs_lookup().get_stop_metadata(stop_id)

        if stop_metadata is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stop {stop_id} not found in static GTFS data",
            )

        feed = await fetch_trip_updates()
        predictor = get_predictor()

        trips = []

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue

            features_list = extract_trip_features(entity.trip_update)

            for feature in features_list:
                if feature["stop_id"] != stop_id:
                    continue

                result = predictor.predict(
                    route_id=feature["route_id"],
                    stop_id=feature["stop_id"],
                    prior_skips_this_trip=feature["prior_skips_this_trip"],
                    last_known_delay=feature["last_known_delay"],
                    has_known_delay=feature["has_known_delay"],
                    stops_remaining=feature["stops_remaining"],
                )

                route_metadata = get_gtfs_lookup().get_route_metadata(
                    feature["route_id"]
                )

                trips.append({
                    "trip_id": feature["trip_id"],
                    "route": route_metadata,
                    "skip_probability": result["skip_probability"],
                    "high_confidence_alert": result["high_confidence_alert"],
                    "last_known_delay_seconds": feature["last_known_delay"],
                    "stops_remaining": feature["stops_remaining"],
                })

        trips.sort(
            key=lambda trip: trip["skip_probability"],
            reverse=True,
        )

        highest_skip_probability = (
            trips[0]["skip_probability"]
            if trips
            else 0.0
        )

        return {
            **stop_metadata,
            "prediction_count": len(trips),
            "highest_skip_probability": highest_skip_probability,
            "high_confidence_alert": any(
                trip["high_confidence_alert"]
                for trip in trips
            ),
            "trips": trips,
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Stop risk prediction failed")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.get("/api/v1/stops/search", tags=["Stops"])
def search_stops(q: str, limit: int = 20):
    """
    Search the in-memory static GTFS stop index by name.
    """

    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    limit = min(max(limit, 1), 50)
    query = q.strip().lower()

    matches = []

    for stop in STOPS_INDEX:
        if query in stop["stop_name"].lower():
            matches.append(stop)

            if len(matches) >= limit:
                break

    return {
        "query": q,
        "count": len(matches),
        "stops": matches,
    }


@app.get("/api/v1/live-activity", tags=["Live Activity"])
async def get_live_activity(limit: int = 20):
    """
    Return cached live GTFS-RT activity.

    Live predictions are refreshed by a background worker,
    so this endpoint does not fetch or run the model itself.
    """
    limit = min(max(limit, 1), 100)

    cached = LIVE_ACTIVITY_CACHE["data"]

    if cached is None:
        return {
            "prediction_count": 0,
            "stop_count": 0,
            "stops": [],
            "computed_at": None,
            "status": "warming_up",
        }

    return {
        "prediction_count": cached["prediction_count"],
        "stop_count": cached["stop_count"],
        "stops": cached["stops"][:limit],
        "computed_at": LIVE_ACTIVITY_CACHE["computed_at"],
        "status": "ok",
    }

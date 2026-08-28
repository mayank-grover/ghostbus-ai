from pathlib import Path
"""
GhostBus AI - FastAPI Backend Service

This module serves as the primary REST API backend for GhostBus AI,
providing endpoints for system health, GTFS real-time data ingestion status,
stop predictions, and ghost bus alerts.
"""

import logging
import csv
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


@app.on_event("startup")
async def load_model():
    logger.info("Loading skip prediction model...")
    get_predictor()
    logger.info("Model loaded successfully.")


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
    Search static GTFS stops by name.

    Uses stops.txt directly so search does not initialize the
    full GTFS lookup (which also loads the much larger stop_times.txt).
    """
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    limit = min(max(limit, 1), 50)
    query = q.strip().lower()

    stops_file = Path(__file__).resolve().parent.parent / "data" / "gtfs_static" / "stops.txt"

    matches = []

    with open(stops_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stop_name = row.get("stop_name", "")

            if query in stop_name.lower():
                matches.append({
                    "stop_id": row["stop_id"],
                    "stop_name": stop_name,
                    "latitude": float(row["stop_lat"]),
                    "longitude": float(row["stop_lon"]),
                })

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
    Fetch current GTFS-RT trip updates, aggregate skip predictions by stop,
    and return the highest-risk active stops.
    """

    limit = min(max(limit, 1), 100)

    try:
        feed = await fetch_trip_updates()
        predictor = get_predictor()
        gtfs_lookup = get_gtfs_lookup()

        stop_predictions = {}

        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue

            features_list = extract_trip_features(entity.trip_update)

            for feature in features_list:
                stop_id = feature["stop_id"]
                result = predictor.predict(
                    route_id=feature["route_id"],
                    stop_id=stop_id,
                    prior_skips_this_trip=feature["prior_skips_this_trip"],
                    last_known_delay=feature["last_known_delay"],
                    has_known_delay=feature["has_known_delay"],
                    stops_remaining=feature["stops_remaining"],
                )

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
                else f"Stop {stop_id}"
            )
            lat = stop_metadata["latitude"] if stop_metadata else 0.0
            lon = stop_metadata["longitude"] if stop_metadata else 0.0

            trips.sort(key=lambda t: t["skip_probability"], reverse=True)
            top_trip_data = trips[0] if trips else None

            top_trip = None
            if top_trip_data:
                route_meta = gtfs_lookup.get_route_metadata(
                    top_trip_data["route_id"]
                )
                route_short_name = (
                    route_meta["route_short_name"]
                    if route_meta and "route_short_name" in route_meta
                    else top_trip_data["route_id"]
                )
                top_trip = {
                    "trip_id": top_trip_data["trip_id"],
                    "route_id": top_trip_data["route_id"],
                    "route_short_name": route_short_name,
                }

            highest_skip_prob = trips[0]["skip_probability"] if trips else 0.0
            has_alert = any(t["high_confidence_alert"] for t in trips)

            stops_summary.append({
                "stop_id": stop_id,
                "stop_name": stop_name,
                "latitude": lat,
                "longitude": lon,
                "prediction_count": len(trips),
                "highest_skip_probability": highest_skip_prob,
                "high_confidence_alert": has_alert,
                "top_trip": top_trip,
            })

        stops_summary.sort(
            key=lambda s: s["highest_skip_probability"],
            reverse=True,
        )

        top_stops = stops_summary[:limit]

        return {
            "active_stop_count": len(top_stops),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stops": top_stops,
        }

    except Exception as e:
        logger.exception("Live activity fetch failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


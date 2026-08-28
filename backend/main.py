"""
GhostBus AI - FastAPI Backend Service

This module serves as the primary REST API backend for GhostBus AI,
providing endpoints for system health, GTFS real-time data ingestion status,
stop predictions, and ghost bus alerts.
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from backend.predictor import get_predictor

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

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

"""
GhostBus AI - FastAPI Backend Service

This module serves as the primary REST API backend for GhostBus AI,
providing endpoints for system health, GTFS real-time data ingestion status,
stop predictions, and ghost bus alerts.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostbus-backend")

app = FastAPI(
    title="GhostBus AI API",
    description="Backend API for GhostBus AI transit monitoring and arrival predictions.",
    version="0.1.0"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check route to verify backend service operational status.
    """
    logger.info("Health check endpoint pinged.")
    return {
        "status": "ok",
        "service": "ghostbus-ai-backend",
        "version": "0.1.0"
    }


# TODO: Add API router for GTFS real-time transit data ingestion (/api/v1/ingestion)
# TODO: Add API router for bus stop lookup and route schedules (/api/v1/stops)
# TODO: Add API router for ML delay and ghost bus predictions (/api/v1/predict)
# TODO: Initialize database session management / dependency injection (SQLite / SQLAlchemy)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

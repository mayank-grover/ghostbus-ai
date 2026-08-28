"""
Live GTFS-RT data client for GhostBus AI.
"""

import os
import logging

import httpx
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2

load_dotenv()

logger = logging.getLogger("ghostbus-live-data")


async def fetch_trip_updates():
    """
    Fetch the current SL GTFS-RT TripUpdates feed.

    Returns the parsed GTFS Realtime FeedMessage.
    """

    api_key = os.getenv("TRAFIKLAB_GTFS_RT_API_KEY")

    if not api_key:
        raise RuntimeError(
            "TRAFIKLAB_GTFS_RT_API_KEY is not set. "
            "Add it to your .env file."
        )

    url = "https://opendata.samtrafiken.se/gtfs-rt/sl/TripUpdates.pb"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            url,
            params={"key": api_key},
        )

        response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    logger.info(
        "Fetched GTFS-RT feed with %d entities",
        len(feed.entity),
    )

    return feed

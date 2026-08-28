"""
GhostBus AI - Skip Prediction Module

Loads the trained model and historical feature lookups once at startup,
and computes skip probability for a given trip/stop/route context.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import xgboost as xgb

logger = logging.getLogger("ghostbus-predictor")

ARTIFACTS_DIR = Path(__file__).resolve().parent / "model_artifacts"

FEATURE_COLS = [
    'hour', 'day_of_week', 'is_weekend', 'prior_skips_this_trip',
    'last_known_delay', 'has_known_delay', 'stops_remaining',
    'route_skip_rate', 'route_count',
    'route_hour_skip_rate', 'route_hour_count',
    'stop_skip_rate', 'stop_count', 'delay_trend'
]


class SkipPredictor:
    def __init__(self):
        logger.info("Loading model and lookup tables...")

        self.model = xgb.XGBClassifier()
        self.model.load_model(str(ARTIFACTS_DIR / "skip_model_v2.json"))

        self.route_stats = pd.read_csv(ARTIFACTS_DIR / "lookup_route_stats.csv", dtype={"route_id": str}).set_index("route_id")
        self.stop_stats = pd.read_csv(ARTIFACTS_DIR / "lookup_stop_stats.csv", dtype={"stop_id": str}).set_index("stop_id")
        route_hour_df = pd.read_csv(ARTIFACTS_DIR / "lookup_route_hour_stats.csv", dtype={"route_id": str})
        self.route_hour_stats = route_hour_df.set_index(["route_id", "hour"])
        with open(ARTIFACTS_DIR / "lookup_metadata.json") as f:
            self.metadata = json.load(f)

        self.global_skip_rate = self.metadata["global_skip_rate"]

        logger.info(f"Loaded: {len(self.route_stats)} routes, {len(self.stop_stats)} stops, "
                    f"{len(self.route_hour_stats)} route-hour combos")

    def _lookup_route(self, route_id: str):
        if route_id in self.route_stats.index:
            row = self.route_stats.loc[route_id]
            return float(row["route_skip_rate"]), float(row["route_count"])
        return self.global_skip_rate, 0.0

    def _lookup_stop(self, stop_id: str):
        if stop_id in self.stop_stats.index:
            row = self.stop_stats.loc[stop_id]
            return float(row["stop_skip_rate"]), float(row["stop_count"])
        return self.global_skip_rate, 0.0

    def _lookup_route_hour(self, route_id: str, hour: int):
        key = (route_id, hour)
        if key in self.route_hour_stats.index:
            row = self.route_hour_stats.loc[key]
            return float(row["route_hour_skip_rate"]), float(row["route_hour_count"])
        return self.global_skip_rate, 0.0

    def predict(
        self,
        route_id: str,
        stop_id: str,
        prior_skips_this_trip: int = 0,
        last_known_delay: float = 0.0,
        has_known_delay: int = 0,
        stops_remaining: int = 0,
        current_time: datetime = None,
    ) -> dict:
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        hour = current_time.hour
        day_of_week = current_time.weekday()
        is_weekend = 1 if day_of_week in (5, 6) else 0

        route_skip_rate, route_count = self._lookup_route(route_id)
        stop_skip_rate, stop_count = self._lookup_stop(stop_id)
        route_hour_skip_rate, route_hour_count = self._lookup_route_hour(route_id, hour)

        # delay_trend needs a "previous" delay to compare against; without
        # live trip-history tracking wired up yet, default to 0 (no trend signal).
        # TODO: replace with real trend once live poller tracks per-trip state.
        delay_trend = 0.0

        features = pd.DataFrame([{
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'prior_skips_this_trip': prior_skips_this_trip,
            'last_known_delay': last_known_delay,
            'has_known_delay': has_known_delay,
            'stops_remaining': stops_remaining,
            'route_skip_rate': route_skip_rate,
            'route_count': route_count,
            'route_hour_skip_rate': route_hour_skip_rate,
            'route_hour_count': route_hour_count,
            'stop_skip_rate': stop_skip_rate,
            'stop_count': stop_count,
            'delay_trend': delay_trend,
        }])[FEATURE_COLS].astype('float32')

        prob = float(self.model.predict_proba(features)[0][1])

        return {
            "skip_probability": prob,
            "high_confidence_alert": prob >= 0.99,
            "features_used": {
                "route_skip_rate": route_skip_rate,
                "route_count": route_count,
                "stop_skip_rate": stop_skip_rate,
                "stop_count": stop_count,
                "route_hour_skip_rate": route_hour_skip_rate,
                "route_hour_count": route_hour_count,
                "hour": hour,
                "day_of_week": day_of_week,
            }
        }


_predictor_instance = None

def get_predictor() -> SkipPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = SkipPredictor()
    return _predictor_instance

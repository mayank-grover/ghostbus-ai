import React from 'react';
import { Clock, MapPin, AlertOctagon, ShieldAlert } from 'lucide-react';
import { formatDelay, formatProbability, getRiskLevel, getRiskLabel } from '../utils/formatters';

export default function TripCard({ trip, stopName }) {
  const skipProb = trip.skip_probability ?? 0;
  const riskLevel = getRiskLevel(skipProb);
  const riskLabel = getRiskLabel(skipProb);
  const formattedSkipPct = formatProbability(skipProb);
  const formattedDelay = formatDelay(trip.last_known_delay_seconds);

  const routeShortName = trip.route_short_name || trip.route?.route_short_name || trip.route_id || '—';
  const routeLongName = trip.route?.route_long_name || 'Active Trip';

  return (
    <div className={`trip-card risk-${riskLevel}`}>
      <div className="trip-header">
        <div className="route-badge-box">
          <div className="route-pill" title={`Route ${routeShortName}`}>
            {routeShortName}
          </div>
          <div className="route-details">
            <span className="route-name">{routeLongName}</span>
            <span className="trip-id-sub">Trip #{trip.trip_id}</span>
          </div>
        </div>

        <div className={`risk-pill ${riskLevel}`}>
          {trip.high_confidence_alert && <ShieldAlert size={13} />}
          <span>{formattedSkipPct} · {riskLabel}</span>
        </div>
      </div>

      {/* Probability meter */}
      <div className="risk-meter">
        <div className="meter-track">
          <div
            className={`meter-fill ${riskLevel}`}
            style={{ width: `${Math.max(5, Math.min(100, skipProb * 100))}%` }}
          />
        </div>
      </div>

      {/* Telemetry info */}
      <div className="trip-info-grid">
        <div className="info-item" title="Live schedule delay">
          <Clock size={13} />
          <span>Status: <strong>{formattedDelay}</strong></span>
        </div>

        <div className="info-item" title="Stops remaining until arrival">
          <MapPin size={13} />
          <span>Stops left: <strong>{trip.stops_remaining ?? 0}</strong></span>
        </div>

        {trip.high_confidence_alert && (
          <div className="info-item" style={{ color: 'var(--risk-high)' }}>
            <AlertOctagon size={13} />
            <span><strong>High confidence alert</strong></span>
          </div>
        )}
      </div>
    </div>
  );
}

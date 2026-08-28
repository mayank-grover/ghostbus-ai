import React, { useState, useEffect } from 'react';
import { MapPin, Activity, ShieldAlert, Navigation, RefreshCw, Clock } from 'lucide-react';
import AlertBanner from './AlertBanner';
import TripCard from './TripCard';
import { NoActiveTripsState } from './UIStates';
import { formatProbability, getRiskLevel } from '../utils/formatters';

export default function StopRiskDashboard({ data, lastUpdated, isRefreshing, onRefresh }) {
  const [secondsAgo, setSecondsAgo] = useState(0);

  useEffect(() => {
    if (!lastUpdated) return;

    const calcSeconds = () => {
      const diff = Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 1000);
      setSecondsAgo(Math.max(0, diff));
    };

    calcSeconds();
    const interval = setInterval(calcSeconds, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  if (!data) return null;

  const {
    stop_id,
    stop_name,
    latitude,
    longitude,
    prediction_count = 0,
    highest_skip_probability = 0,
    high_confidence_alert = false,
    trips = [],
  } = data;

  const sortedTrips = [...trips].sort(
    (a, b) => (b.skip_probability ?? 0) - (a.skip_probability ?? 0)
  );

  const peakRiskLevel = getRiskLevel(highest_skip_probability);
  const updatedText = secondsAgo < 5 ? 'Updated just now' : `Updated ${secondsAgo}s ago`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Dashboard Top Panel */}
      <div className="glass-panel dashboard-header">
        <div className="stop-title-row">
          <div>
            <h1 className="stop-title">{stop_name}</h1>
            <div className="stop-meta">
              <span className="meta-chip">
                <MapPin size={12} /> ID #{stop_id}
              </span>
              {latitude !== undefined && longitude !== undefined && (
                <span className="meta-chip">
                  <Navigation size={12} /> {latitude.toFixed(4)}, {longitude.toFixed(4)}
                </span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="meta-chip"
              onClick={onRefresh}
              disabled={isRefreshing}
              style={{
                cursor: 'pointer',
                border: '1px solid var(--border-subtle)',
                background: 'rgba(6, 182, 212, 0.1)',
                color: 'var(--accent-cyan)',
                padding: '0.35rem 0.65rem',
                borderRadius: '0.5rem',
                transition: 'all 0.2s ease',
              }}
              title="Click to manually refresh live risk data"
            >
              <RefreshCw size={12} className={isRefreshing ? 'spinner' : ''} />
              <span>Live · {isRefreshing ? 'Refreshing...' : updatedText}</span>
            </button>

            <div className={`risk-pill ${peakRiskLevel}`} style={{ fontSize: '0.9rem' }}>
              Peak Risk: {formatProbability(highest_skip_probability)}
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Live Trips Tracked</span>
            <span className="stat-value">{prediction_count}</span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Highest Skip Risk</span>
            <span className={`stat-value risk-${peakRiskLevel}`} style={{ color: `var(--risk-${peakRiskLevel})` }}>
              {formatProbability(highest_skip_probability)}
            </span>
          </div>

          <div className="stat-card">
            <span className="stat-label">Ghost Bus Alert</span>
            <span
              className="stat-value"
              style={{
                color: high_confidence_alert ? 'var(--risk-high)' : 'var(--risk-low)',
                fontSize: '1.1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              {high_confidence_alert ? (
                <>
                  <ShieldAlert size={18} /> ALERT ACTIVE
                </>
              ) : (
                'NORMAL'
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Alert Banner if High Confidence Alert is triggered */}
      {high_confidence_alert && <AlertBanner />}

      {/* Trips Section */}
      <div className="trips-section">
        <div className="section-header">
          <div className="section-title">
            <Activity size={18} style={{ color: 'var(--accent-cyan)' }} />
            <span>Live Incoming Trips</span>
            <span className="badge-count">{sortedTrips.length}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {isRefreshing && (
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                Syncing live telemetry...
              </span>
            )}
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Sorted by Highest Risk First
            </span>
          </div>
        </div>

        {sortedTrips.length > 0 ? (
          sortedTrips.map((trip) => (
            <TripCard key={trip.trip_id} trip={trip} stopName={stop_name} />
          ))
        ) : (
          <NoActiveTripsState stopName={stop_name} />
        )}
      </div>
    </div>
  );
}

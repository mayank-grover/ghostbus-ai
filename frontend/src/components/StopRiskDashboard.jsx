import React, { useState, useEffect } from 'react';
import { MapPin, Activity, ShieldAlert, Navigation, RefreshCw } from 'lucide-react';
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
    <div className="stop-dashboard-scroll-view">
      {/* Sticky Xcode/Linear Style Inspector Header */}
      <div className="stop-header-sticky">
        <div className="stop-title-row">
          <div>
            <h2 className="stop-title">{stop_name}</h2>
            <div className="stop-meta">
              <span className="meta-chip">
                <MapPin size={11} /> ID #{stop_id}
              </span>
              {latitude !== undefined && longitude !== undefined && (
                <span className="meta-chip">
                  <Navigation size={11} /> {latitude.toFixed(4)}, {longitude.toFixed(4)}
                </span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="refresh-pill-btn"
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Click to manually refresh live risk data"
            >
              <RefreshCw size={11} className={isRefreshing ? 'spinner' : ''} />
              <span>{isRefreshing ? 'Refreshing...' : updatedText}</span>
            </button>

            <span className={`risk-badge ${peakRiskLevel}`} style={{ fontSize: '0.78rem' }}>
              Peak Risk: {formatProbability(highest_skip_probability)}
            </span>
          </div>
        </div>

        {/* Metric Inspector Grid */}
        <div className="inspector-stats-grid">
          <div className="inspector-stat-tile">
            <span className="stat-tile-label">Live Trips Tracked</span>
            <span className="stat-tile-value">{prediction_count}</span>
          </div>

          <div className="inspector-stat-tile">
            <span className="stat-tile-label">Highest Skip Risk</span>
            <span className={`stat-tile-value risk-${peakRiskLevel}`} style={{ color: `var(--risk-${peakRiskLevel})` }}>
              {formatProbability(highest_skip_probability)}
            </span>
          </div>

          <div className="inspector-stat-tile">
            <span className="stat-tile-label">Ghost Bus Alert</span>
            <span
              className="stat-tile-value"
              style={{
                color: high_confidence_alert ? 'var(--risk-high)' : 'var(--risk-low)',
                fontSize: '0.9rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              {high_confidence_alert ? (
                <>
                  <ShieldAlert size={14} /> ALERT
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

      {/* Scrollable Trips Section */}
      <div className="trips-section">
        <div className="section-header">
          <div className="section-title">
            <Activity size={15} style={{ color: 'var(--accent-cyan)' }} />
            <span>Live Incoming Trips</span>
            <span className="badge-count">{sortedTrips.length}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {isRefreshing && (
              <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                Syncing...
              </span>
            )}
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Highest Risk First
            </span>
          </div>
        </div>

        {sortedTrips.length > 0 ? (
          <div className="trips-list-container">
            {sortedTrips.map((trip) => (
              <TripCard key={trip.trip_id} trip={trip} stopName={stop_name} />
            ))}
          </div>
        ) : (
          <NoActiveTripsState stopName={stop_name} />
        )}
      </div>
    </div>
  );
}

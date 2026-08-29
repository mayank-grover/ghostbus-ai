import React from 'react';
import { Activity, ShieldAlert, RefreshCw, ChevronRight, Loader2, AlertCircle } from 'lucide-react';
import { formatProbability, getRiskLevel } from '../utils/formatters';

export default function LiveActivityRadar({
  stops = [],
  isLoading = false,
  isRefreshing = false,
  error = null,
  onSelectStop,
  currentStopId,
  onRefreshLive,
}) {
  // Radar displays only the top 20 highest-risk active stops
  const radarStops = stops.slice(0, 20);

  return (
    <div className="radar-card">
      <div className="pane-header">
        <div className="pane-title-group">
          <Activity size={14} className="accent-icon" />
          <span className="pane-title">Live Activity Radar</span>
          <span className="pane-count">Top 20</span>
        </div>

        <button
          type="button"
          className="action-link-btn"
          onClick={onRefreshLive}
          disabled={isRefreshing}
          title="Manually refresh live activity data"
        >
          <RefreshCw size={11} className={isRefreshing ? 'spinner' : ''} />
          {isRefreshing ? 'Updating…' : 'Refresh'}
        </button>
      </div>

      {isLoading ? (
        <div className="pane-loading">
          <Loader2 size={20} className="spinner" />
          <span>Scanning network telemetry…</span>
        </div>
      ) : error && stops.length === 0 ? (
        <div className="pane-loading" style={{ gap: '0.65rem' }}>
          <AlertCircle size={20} style={{ color: 'var(--risk-crit)' }} />
          <span style={{ color: '#fca5a5', fontSize: '0.78rem' }}>{error}</span>
          <button type="button" className="retry-btn" onClick={onRefreshLive}>
            Retry
          </button>
        </div>
      ) : stops.length === 0 ? (
        <div className="pane-loading">
          <span>No active transit trips in live feed.</span>
        </div>
      ) : (
        <div className="radar-feed-list">
          {radarStops.map((stop) => {
            const riskLevel = getRiskLevel(stop.highest_skip_probability);
            const isSelected = currentStopId === stop.stop_id;
            const topTrip = stop.trips?.reduce(
              (best, trip) =>
                !best || (trip.skip_probability ?? 0) > (best.skip_probability ?? 0)
                  ? trip
                  : best,
              null
            );
            const routeShortName =
              topTrip?.route_short_name || topTrip?.route_id || '—';

            return (
              <button
                key={stop.stop_id}
                type="button"
                className={`radar-row-item ${isSelected ? 'is-selected' : ''}`}
                onClick={() => onSelectStop(stop)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flex: 1, minWidth: 0 }}>
                  <div className="route-tag">{routeShortName}</div>

                  <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', minWidth: 0 }}>
                    <span className="row-stop-name">{stop.stop_name}</span>
                    <span className="row-stop-sub">
                      #{stop.stop_id} · {stop.prediction_count} {stop.prediction_count === 1 ? 'trip' : 'trips'}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexShrink: 0 }}>
                  {stop.high_confidence_alert && (
                    <ShieldAlert size={13} style={{ color: 'var(--risk-high)' }} title="High Confidence Alert" />
                  )}
                  <span className={`risk-badge ${riskLevel}`}>
                    {formatProbability(stop.highest_skip_probability)}
                  </span>
                  <ChevronRight size={13} className="row-chevron" />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

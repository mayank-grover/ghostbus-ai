import React, { useState, useEffect, useCallback } from 'react';
import { Activity, ShieldAlert, RefreshCw, ChevronRight, Loader2, AlertCircle } from 'lucide-react';
import { getLiveActivity } from '../services/api';
import { formatProbability, getRiskLevel } from '../utils/formatters';

export default function LiveActivityPanel({ onSelectStop, currentStopId }) {
  const [stops, setStops] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchLiveActivity = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      setIsLoading(true);
      setError(null);
    } else {
      setIsRefreshing(true);
    }

    try {
      const data = await getLiveActivity(20);
      setStops(data.stops || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch live activity:', err);
      if (!isBackground) {
        setError(err.message || 'Failed to fetch live activity telemetry.');
      }
      // Preserve existing stops data silently on background failure
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchLiveActivity(false);

    // 20-second automatic background refresh
    const intervalId = setInterval(() => {
      fetchLiveActivity(true);
    }, 20000);

    return () => clearInterval(intervalId);
  }, [fetchLiveActivity]);

  return (
    <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
      <div className="section-header" style={{ marginBottom: '1rem' }}>
        <div className="section-title">
          <Activity size={20} style={{ color: 'var(--accent-cyan)' }} />
          <span>Live Activity Radar</span>
          <span className="badge-count" title="Top active high-risk stops across Stockholm network">
            Top {stops.length} Active Stops
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {isRefreshing && (
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
              Updating...
            </span>
          )}
          <button
            type="button"
            className="meta-chip"
            onClick={() => fetchLiveActivity(stops.length > 0)}
            disabled={isRefreshing}
            style={{
              cursor: 'pointer',
              border: '1px solid var(--border-subtle)',
              background: 'rgba(6, 182, 212, 0.08)',
              color: 'var(--accent-cyan)',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.35rem',
            }}
            title="Click to manually refresh live activity"
          >
            <RefreshCw size={12} className={isRefreshing ? 'spinner' : ''} />
            <span>20s Refresh</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <Loader2 size={28} className="spinner" style={{ margin: '0 auto 0.75rem' }} />
          <p style={{ fontSize: '0.9rem' }}>Scanning active network telemetry for high-risk stops...</p>
        </div>
      ) : error && stops.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <AlertCircle size={28} style={{ color: 'var(--risk-high)', margin: '0 auto 0.5rem' }} />
          <p style={{ fontSize: '0.9rem', color: '#fca5a5' }}>{error}</p>
          <button
            type="button"
            className="retry-btn"
            style={{ marginTop: '0.75rem', fontSize: '0.8rem', padding: '0.35rem 0.85rem' }}
            onClick={() => fetchLiveActivity(false)}
          >
            Retry Radar
          </button>
        </div>
      ) : stops.length === 0 ? (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          No active transit trips detected in live feed currently.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '420px', overflowY: 'auto' }}>
          {stops.map((stop) => {
            const riskLevel = getRiskLevel(stop.highest_skip_probability);
            const isSelected = currentStopId === stop.stop_id;
            const routeShortName = stop.top_trip?.route_short_name || stop.top_trip?.route_id || 'Bus';

            return (
              <button
                key={stop.stop_id}
                type="button"
                className={`dropdown-item ${isSelected ? 'focused' : ''}`}
                onClick={() => onSelectStop(stop)}
                style={{
                  width: '100%',
                  background: isSelected ? 'rgba(6, 182, 212, 0.18)' : 'rgba(0, 0, 0, 0.25)',
                  border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                  borderRadius: '0.65rem',
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: 0 }}>
                  <div className="route-pill" style={{ minWidth: '40px', height: '32px', fontSize: '0.95rem' }}>
                    {routeShortName}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', minWidth: 0 }}>
                    <span className="stop-name" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {stop.stop_name}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Stop #{stop.stop_id} • {stop.prediction_count} live {stop.prediction_count === 1 ? 'trip' : 'trips'}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexShrink: 0 }}>
                  {stop.high_confidence_alert && (
                    <ShieldAlert size={16} style={{ color: 'var(--risk-high)' }} title="High Confidence Alert Active" />
                  )}

                  <div className={`risk-pill ${riskLevel}`} style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}>
                    {formatProbability(stop.highest_skip_probability)}
                  </div>

                  <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { Loader2, Search, Bus, AlertCircle, RefreshCw } from 'lucide-react';

export function LoadingState({ stopName }) {
  return (
    <div className="glass-panel state-box">
      <Loader2 size={36} className="spinner" />
      <span className="state-title">Analyzing Telemetry for {stopName || 'Stop'}...</span>
      <span className="state-desc">Fetching live GTFS-RT trip updates & computing XGBoost skip risk.</span>
    </div>
  );
}

export function InitialState() {
  return (
    <div className="glass-panel state-box">
      <Search size={40} className="state-icon" />
      <span className="state-title">Search Your Bus Stop</span>
      <span className="state-desc">
        Type a stop name in the search box above (e.g. Slussen, T-Centralen) to view real-time ghost bus skip predictions and delay telemetry.
      </span>
    </div>
  );
}

export function NoActiveTripsState({ stopName }) {
  return (
    <div className="glass-panel state-box">
      <Bus size={40} className="state-icon" />
      <span className="state-title">No Active Live Trips Found</span>
      <span className="state-desc">
        There are currently no active live trips detected in the GTFS-RT feed approaching <strong>{stopName}</strong> right now.
      </span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="glass-panel state-box" style={{ borderColor: 'var(--risk-high-border)' }}>
      <AlertCircle size={40} style={{ color: 'var(--risk-high)' }} />
      <span className="state-title" style={{ color: '#fca5a5' }}>Failed to Load Live Risk Data</span>
      <span className="state-desc">{message || 'Unable to connect to GhostBus AI backend server.'}</span>
      {onRetry && (
        <button type="button" className="retry-btn" onClick={onRetry}>
          <RefreshCw size={14} style={{ display: 'inline', marginRight: '0.4rem' }} />
          Retry Connection
        </button>
      )}
    </div>
  );
}

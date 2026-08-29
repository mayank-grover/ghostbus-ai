import React from 'react';
import { Loader2, Search, Bus, AlertCircle, RefreshCw } from 'lucide-react';

export function LoadingState({ stopName }) {
  return (
    <div className="state-box">
      <Loader2 size={30} className="spinner" />
      <span className="state-title">Analyzing Telemetry for {stopName || 'Stop'}...</span>
      <span className="state-desc">Fetching live GTFS-RT updates & computing XGBoost skip risk.</span>
    </div>
  );
}

export function InitialState() {
  return (
    <div className="state-box">
      <Search size={32} className="state-icon" />
      <span className="state-title">Search Your Bus Stop</span>
      <span className="state-desc">
        Type a stop name in the search bar above (e.g. Slussen, T-Centralen) to view real-time predictions.
      </span>
    </div>
  );
}

export function EmptyStopState() {
  return (
    <div className="mac-inspector-empty">
      {/* Upper Inspector Toolbar Header */}
      <div className="inspector-toolbar">
        <span className="toolbar-label">INSPECTOR WORKSPACE</span>
        <span className="toolbar-status">NO SELECTION</span>
      </div>

      {/* Main Workspace Body */}
      <div className="inspector-body">
        <h3 className="inspector-title">No Stop Selected</h3>
        <p className="inspector-subtext">
          Select a bus stop to inspect real-time GTFS-RT telemetry, live incoming trips, and XGBoost ML skip predictions.
        </p>

        <div className="inspector-guide">
          <span className="guide-label">SELECT VIA:</span>
          <div className="guide-pills">
            <span className="guide-pill">⌘ Search bar above</span>
            <span className="guide-pill">Live Activity Radar list</span>
            <span className="guide-pill">Live Risk Map markers</span>
          </div>
        </div>
      </div>

      {/* Subtle Geometric Transit Schematic Art */}
      <div className="inspector-schematic-art">
        <svg viewBox="0 0 440 220" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M 30 50 L 140 50 L 210 120 L 410 120" stroke="rgba(255,255,255,0.04)" strokeWidth="1.5" strokeDasharray="3 3" />
          <path d="M 50 160 L 180 160 L 250 90 L 390 90" stroke="rgba(56,189,248,0.08)" strokeWidth="1.5" />
          <path d="M 140 50 L 180 160" stroke="rgba(255,255,255,0.03)" strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="140" cy="50" r="3.5" fill="rgba(255,255,255,0.12)" />
          <circle cx="210" cy="120" r="4" fill="rgba(56,189,248,0.3)" />
          <circle cx="250" cy="90" r="3.5" fill="rgba(255,255,255,0.12)" />
        </svg>
      </div>
    </div>
  );
}

export function NoActiveTripsState({ stopName }) {
  return (
    <div className="state-box">
      <Bus size={32} className="state-icon" />
      <span className="state-title">No Active Live Trips Found</span>
      <span className="state-desc">
        There are currently no active live trips detected approaching <strong>{stopName}</strong> right now.
      </span>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-box" style={{ borderColor: 'var(--risk-high-border)' }}>
      <AlertCircle size={32} style={{ color: 'var(--risk-high)' }} />
      <span className="state-title" style={{ color: '#fca5a5' }}>Failed to Load Live Risk Data</span>
      <span className="state-desc">{message || 'Unable to connect to GhostBus AI backend server.'}</span>
      {onRetry && (
        <button type="button" className="retry-btn" onClick={onRetry}>
          <RefreshCw size={12} style={{ display: 'inline', marginRight: '0.4rem' }} />
          Retry Connection
        </button>
      )}
    </div>
  );
}

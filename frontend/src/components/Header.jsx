import React from 'react';
import { Bus, Radio } from 'lucide-react';

export default function Header() {
  return (
    <header className="mac-header">
      <div className="mac-header-main">
        <div className="brand-group">
          <div className="brand-icon-box">
            <Bus size={20} className="brand-icon" />
          </div>
          <div className="brand-text">
            <div className="brand-name-row">
              <h1 className="brand-title">GhostBus AI</h1>
              <span className="app-version-tag">v2.4</span>
            </div>
            <p className="brand-subtitle">
              Real-time urban transit intelligence & ML skip prediction
            </p>
          </div>
        </div>

        <div className="mac-status-pill" title="Connected to SL GTFS-RT Live Telemetry">
          <Radio size={12} className="status-radio-icon" />
          <span className="pulse-dot" />
          <span>SL GTFS-RT LIVE</span>
        </div>
      </div>
    </header>
  );
}

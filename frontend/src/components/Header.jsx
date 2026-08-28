import React from 'react';
import { Bus, Radio } from 'lucide-react';

export default function Header() {
  return (
    <header className="header-container">
      <div className="brand-row">
        <div className="brand-title">
          <Bus className="brand-icon" size={32} />
          <span>GhostBus AI</span>
        </div>
        <div className="live-badge" title="Connected to SL GTFS-RT Live Telemetry">
          <span className="pulse-dot"></span>
          <span>SL GTFS-RT LIVE</span>
        </div>
      </div>
      <p className="header-subtitle">
        Real-time ML skip prediction & ghost bus telemetry dashboard
      </p>
    </header>
  );
}

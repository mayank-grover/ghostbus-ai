import React from 'react';
import { AlertTriangle } from 'lucide-react';

export default function AlertBanner() {
  return (
    <div className="alert-banner" role="alert">
      <AlertTriangle className="alert-icon" size={24} />
      <div className="alert-content">
        <span className="alert-title">High Confidence Ghost Bus Alert</span>
        <span className="alert-desc">
          One or more incoming bus trips show critical skip probability for this stop based on live GTFS-RT telemetry.
        </span>
      </div>
    </div>
  );
}

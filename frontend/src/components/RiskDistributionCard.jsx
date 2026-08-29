import React from 'react';
import { BarChart3, AlertTriangle } from 'lucide-react';

/**
 * Calculates skip-risk prediction distribution across ALL trips inside stops[].trips[].
 * Risk Buckets:
 * - Low: < 25% (0.0 to < 0.25)
 * - Moderate: 25% to < 75% (0.25 to < 0.75)
 * - High: 75% to < 99% (0.75 to < 0.99)
 * - Critical: >= 99% (>= 0.99)
 */
export function calculateRiskDistribution(stops) {
  let low = 0;
  let moderate = 0;
  let high = 0;
  let critical = 0;
  let total = 0;

  if (Array.isArray(stops)) {
    for (const stop of stops) {
      if (Array.isArray(stop.trips)) {
        for (const trip of stop.trips) {
          const p = typeof trip.skip_probability === 'number' ? trip.skip_probability : 0;
          total++;
          if (p >= 0.99) {
            critical++;
          } else if (p >= 0.75) {
            high++;
          } else if (p >= 0.25) {
            moderate++;
          } else {
            low++;
          }
        }
      }
    }
  }

  const lowPct = total > 0 ? Math.round((low / total) * 100) : 0;
  const modPct = total > 0 ? Math.round((moderate / total) * 100) : 0;
  const highPct = total > 0 ? Math.round((high / total) * 100) : 0;
  const critPct = total > 0 ? Math.round((critical / total) * 100) : 0;

  return { total, low, moderate, high, critical, lowPct, modPct, highPct, critPct };
}

export default function RiskDistributionCard({ stops, isLoading }) {
  const { total, low, moderate, high, critical, lowPct, modPct, highPct, critPct } =
    calculateRiskDistribution(stops);

  return (
    <div className="risk-distribution-card">
      {/* Header */}
      <div className="pane-header">
        <div className="pane-title-group">
          <BarChart3 size={14} className="accent-icon" />
          <span className="pane-title">Skip Risk Distribution</span>
          <span className="pane-count">{total.toLocaleString()} predictions</span>
        </div>
      </div>

      <div style={{ padding: '0.75rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {/* Stacked bar */}
        <div className="dist-bar-track">
          {total > 0 && (
            <>
              {low > 0 && (
                <div className="dist-bar-segment segment-low" style={{ width: `${(low / total) * 100}%` }} title={`Low: ${lowPct}%`} />
              )}
              {moderate > 0 && (
                <div className="dist-bar-segment segment-moderate" style={{ width: `${(moderate / total) * 100}%` }} title={`Moderate: ${modPct}%`} />
              )}
              {high > 0 && (
                <div className="dist-bar-segment segment-high" style={{ width: `${(high / total) * 100}%` }} title={`High: ${highPct}%`} />
              )}
              {critical > 0 && (
                <div className="dist-bar-segment segment-critical" style={{ width: `${(critical / total) * 100}%` }} title={`Critical: ${critPct}%`} />
              )}
            </>
          )}
          {total === 0 && (
            <div style={{ width: '100%', height: '100%', background: 'rgba(255,255,255,0.05)', borderRadius: '99px' }} />
          )}
        </div>

        {/* 4-column grid */}
        <div className="dist-grid-4col">
          <div className="dist-col-item">
            <div className="dist-col-header">
              <span className="dist-dot dot-low" />
              <span>Low</span>
            </div>
            <span className="dist-col-value">{lowPct}%</span>
            <span className="dist-col-sub">{low.toLocaleString()}</span>
          </div>

          <div className="dist-col-item">
            <div className="dist-col-header">
              <span className="dist-dot dot-moderate" />
              <span>Moderate</span>
            </div>
            <span className="dist-col-value">{modPct}%</span>
            <span className="dist-col-sub">{moderate.toLocaleString()}</span>
          </div>

          <div className="dist-col-item">
            <div className="dist-col-header">
              <span className="dist-dot dot-high" />
              <span>High</span>
            </div>
            <span className="dist-col-value">{highPct}%</span>
            <span className="dist-col-sub">{high.toLocaleString()}</span>
          </div>

          <div className="dist-col-item">
            <div className="dist-col-header">
              <span className="dist-dot dot-critical" />
              <span>Critical</span>
            </div>
            <span className="dist-col-value risk-crit-text">{critPct}%</span>
            <span className="dist-col-sub">{critical.toLocaleString()}</span>
          </div>
        </div>

        {/* Critical alert strip */}
        {critical > 0 && (
          <div className="dist-alert-strip">
            <AlertTriangle size={12} />
            <span>
              <strong>{critical.toLocaleString()}</strong> active {critical === 1 ? 'trip' : 'trips'} at ≥99% skip risk
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

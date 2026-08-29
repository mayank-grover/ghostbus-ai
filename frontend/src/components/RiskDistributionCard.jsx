import React from 'react';
import { BarChart3, Info, AlertTriangle } from 'lucide-react';

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

  return {
    total,
    low,
    moderate,
    high,
    critical,
    lowPct,
    modPct,
    highPct,
    critPct,
  };
}

export default function RiskDistributionCard({ stops, isLoading }) {
  const { total, low, moderate, high, critical, lowPct, modPct, highPct, critPct } =
    calculateRiskDistribution(stops);

  return (
    <div className="glass-panel risk-distribution-card">
      <div className="dist-card-header">
        <div className="dist-card-title-group">
          <BarChart3 size={18} className="dist-header-icon" />
          <h3 className="dist-card-title">Skip Risk Distribution</h3>
        </div>
        <div
          className="dist-tooltip-wrapper"
          title="Distribution of current model-predicted skip probabilities across active trips."
        >
          <Info size={15} className="dist-info-icon" />
        </div>
      </div>

      <p className="dist-card-subtitle">
        Distribution of current model-predicted skip probabilities.
      </p>

      <div className="dist-total-row">
        <span className="dist-total-count">{total} active predictions</span>
      </div>

      {/* Horizontal Stacked Bar */}
      <div className="dist-stacked-bar-container">
        {total > 0 ? (
          <div className="dist-stacked-bar">
            {low > 0 && (
              <div
                className="dist-bar-segment segment-low"
                style={{ width: `${(low / total) * 100}%` }}
                title={`Low (<25%): ${lowPct}% (${low})`}
              />
            )}
            {moderate > 0 && (
              <div
                className="dist-bar-segment segment-moderate"
                style={{ width: `${(moderate / total) * 100}%` }}
                title={`Moderate (25-74%): ${modPct}% (${moderate})`}
              />
            )}
            {high > 0 && (
              <div
                className="dist-bar-segment segment-high"
                style={{ width: `${(high / total) * 100}%` }}
                title={`High (75-98%): ${highPct}% (${high})`}
              />
            )}
            {critical > 0 && (
              <div
                className="dist-bar-segment segment-critical"
                style={{ width: `${(critical / total) * 100}%` }}
                title={`Critical (≥99%): ${critPct}% (${critical})`}
              />
            )}
          </div>
        ) : (
          <div className="dist-stacked-bar empty">
            <div className="dist-bar-segment segment-empty" style={{ width: '100%' }} />
          </div>
        )}
      </div>

      {/* Legend / Bucket List */}
      <div className="dist-bucket-list">
        <div className="dist-bucket-item">
          <div className="dist-bucket-left">
            <span className="dist-dot dot-low"></span>
            <span className="dist-bucket-name">Low (&lt;25%)</span>
          </div>
          <div className="dist-bucket-right">
            <span className="dist-bucket-pct">{lowPct}%</span>
            <span className="dist-bucket-sep">·</span>
            <span className="dist-bucket-count">{low}</span>
          </div>
        </div>

        <div className="dist-bucket-item">
          <div className="dist-bucket-left">
            <span className="dist-dot dot-moderate"></span>
            <span className="dist-bucket-name">Moderate (25–74%)</span>
          </div>
          <div className="dist-bucket-right">
            <span className="dist-bucket-pct">{modPct}%</span>
            <span className="dist-bucket-sep">·</span>
            <span className="dist-bucket-count">{moderate}</span>
          </div>
        </div>

        <div className="dist-bucket-item">
          <div className="dist-bucket-left">
            <span className="dist-dot dot-high"></span>
            <span className="dist-bucket-name">High (75–98%)</span>
          </div>
          <div className="dist-bucket-right">
            <span className="dist-bucket-pct">{highPct}%</span>
            <span className="dist-bucket-sep">·</span>
            <span className="dist-bucket-count">{high}</span>
          </div>
        </div>

        <div className="dist-bucket-item">
          <div className="dist-bucket-left">
            <span className="dist-dot dot-critical"></span>
            <span className="dist-bucket-name">Critical (≥99%)</span>
          </div>
          <div className="dist-bucket-right">
            <span className="dist-bucket-pct">{critPct}%</span>
            <span className="dist-bucket-sep">·</span>
            <span className="dist-bucket-count">{critical}</span>
          </div>
        </div>
      </div>

      {/* Summary Highlight */}
      <div className={`dist-summary-pill ${critical > 0 ? 'alert-active' : ''}`}>
        {critical > 0 && <AlertTriangle size={14} className="dist-alert-icon" />}
        <span>
          <strong>{critical}</strong> {critical === 1 ? 'prediction' : 'predictions'} at ≥99% risk
        </span>
      </div>
    </div>
  );
}

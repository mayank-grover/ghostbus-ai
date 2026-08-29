import React, { useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Map, Maximize2 } from 'lucide-react';
import { formatProbability, getRiskLabel } from '../utils/formatters';

// Risk classification strictly adhering to system thresholds:
// Low: <25%, Moderate: 25-74%, High: 75-98%, Critical: >=99%
function classifyRisk(prob) {
  if (prob >= 0.99) return 'critical';
  if (prob >= 0.75) return 'high';
  if (prob >= 0.25) return 'medium';
  return 'low';
}

function lerp(a, b, t) {
  return a + (b - a) * Math.min(1, Math.max(0, t));
}

// Compute dynamic zoom-dependent styles so low-risk markers stay quiet when zoomed out
// and high/critical markers always stand out prominently with strong outlines and halos.
function getMarkerStyle(level, isSelected, zoom) {
  // Zoom normalization between 9 (zoomed out city region) and 16 (neighborhood)
  const z = Math.max(9, Math.min(zoom || 10, 16));
  const t = (z - 9) / 7;

  switch (level) {
    case 'critical':
      return {
        radius: isSelected ? lerp(8.5, 12, t) + 4 : lerp(8.5, 12, t),
        fillColor: '#ef4444',
        color: '#450a0a',       // Deep dark red border for maximum contrast against any background
        weight: isSelected ? 3 : 2,
        opacity: 1,
        fillOpacity: 0.95,
        haloRadius: lerp(15, 22, t),
        haloFill: '#ef4444',
        haloOpacity: 0.22,
      };
    case 'high':
      return {
        radius: isSelected ? lerp(6.5, 9.5, t) + 3 : lerp(6.5, 9.5, t),
        fillColor: '#f97316',
        color: '#431407',       // Deep dark contrast border
        weight: isSelected ? 2.5 : 1.5,
        opacity: 0.95,
        fillOpacity: 0.9,
        haloRadius: lerp(11, 16, t),
        haloFill: '#ea580c',
        haloOpacity: 0.16,
      };
    case 'medium':
      return {
        radius: isSelected ? lerp(4, 6.5, t) + 2 : lerp(3.5, 6, t),
        fillColor: '#f59e0b',
        color: '#78350f',
        weight: isSelected ? 2 : 1,
        opacity: lerp(0.55, 0.85, t),
        fillOpacity: lerp(0.45, 0.75, t),
        haloRadius: null,
        haloFill: null,
        haloOpacity: 0,
      };
    case 'low':
    default:
      return {
        // Zoomed out: low-risk is tiny and low-opacity to prevent drowning the map in green
        radius: isSelected ? lerp(3, 5, t) + 2 : lerp(1.8, 3.8, t),
        fillColor: '#22c55e',
        color: '#14532d',
        weight: isSelected ? 2 : 0.6,
        opacity: isSelected ? 0.9 : lerp(0.22, 0.6, t),
        fillOpacity: isSelected ? 0.85 : lerp(0.18, 0.5, t),
        haloRadius: null,
        haloFill: null,
        haloOpacity: 0,
      };
  }
}

// Low painted first, so high and critical layers are always on top
const PAINT_ORDER = ['low', 'medium', 'high', 'critical'];

export default function LiveRiskMap({ stops = [], onSelectStop, currentStopId }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const canvasRendererRef = useRef(null);
  const layerGroupRef = useRef(null);

  const stopsRef = useRef(stops);
  const currentStopRef = useRef(currentStopId);
  const onSelectStopRef = useRef(onSelectStop);

  stopsRef.current = stops;
  currentStopRef.current = currentStopId;
  onSelectStopRef.current = onSelectStop;

  const validStops = stops.filter(
    (s) =>
      typeof s.latitude === 'number' &&
      typeof s.longitude === 'number' &&
      !isNaN(s.latitude) &&
      !isNaN(s.longitude) &&
      s.latitude !== 0 &&
      s.longitude !== 0
  );

  const renderMarkers = useCallback((stopsList, zoom, selectedId) => {
    const layerGroup = layerGroupRef.current;
    const canvasRenderer = canvasRendererRef.current;
    if (!layerGroup || !canvasRenderer) return;

    layerGroup.clearLayers();

    // Group stops into risk buckets
    const buckets = { low: [], medium: [], high: [], critical: [] };
    stopsList.forEach((stop) => {
      const prob = stop.highest_skip_probability ?? 0;
      const level = classifyRisk(prob);
      buckets[level].push(stop);
    });

    // 1. Paint halos first for high/critical to ensure they render underneath their own markers
    ['high', 'critical'].forEach((level) => {
      buckets[level].forEach((stop) => {
        const isSelected = selectedId === stop.stop_id;
        const style = getMarkerStyle(level, isSelected, zoom);
        if (style.haloRadius && style.haloFill) {
          L.circleMarker([stop.latitude, stop.longitude], {
            renderer: canvasRenderer,
            radius: style.haloRadius,
            fillColor: style.haloFill,
            color: 'transparent',
            weight: 0,
            opacity: 0,
            fillOpacity: style.haloOpacity,
            interactive: false,
          }).addTo(layerGroup);
        }
      });
    });

    // 2. Paint core markers in strict order (low -> medium -> high -> critical)
    PAINT_ORDER.forEach((level) => {
      buckets[level].forEach((stop) => {
        const prob = stop.highest_skip_probability ?? 0;
        const isSelected = selectedId === stop.stop_id;
        const style = getMarkerStyle(level, isSelected, zoom);

        const marker = L.circleMarker([stop.latitude, stop.longitude], {
          renderer: canvasRenderer,
          radius: style.radius,
          fillColor: style.fillColor,
          color: isSelected ? '#ffffff' : style.color,
          weight: isSelected ? 3 : style.weight,
          opacity: style.opacity,
          fillOpacity: style.fillOpacity,
        });

        // 3. Selection ring on top of selected stop
        if (isSelected) {
          L.circleMarker([stop.latitude, stop.longitude], {
            renderer: canvasRenderer,
            radius: style.radius + 5,
            fillColor: 'transparent',
            color: '#ffffff',
            weight: 2,
            opacity: 0.7,
            fillOpacity: 0,
            interactive: false,
          }).addTo(layerGroup);
        }

        // Popup construction
        const riskLabel = getRiskLabel(prob);
        const formattedProb = formatProbability(prob);
        const topTrip = stop.trips?.reduce(
          (best, trip) =>
            !best || (trip.skip_probability ?? 0) > (best.skip_probability ?? 0) ? trip : best,
          null
        );
        const routeShortName = topTrip?.route_short_name || topTrip?.route_id || null;

        const popupHtml = buildPopupHtml(stop, level, formattedProb, riskLabel, routeShortName);

        marker.bindPopup(popupHtml, {
          className: 'ghostbus-leaflet-popup',
          maxWidth: 240,
        });

        marker.on('popupopen', () => {
          const btn = document.getElementById(`popup-btn-${stop.stop_id}`);
          if (btn) {
            btn.onclick = () => {
              if (onSelectStopRef.current) onSelectStopRef.current(stop);
            };
          }
        });

        layerGroup.addLayer(marker);
      });
    });
  }, []);

  // Initialize Leaflet map instance once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const canvasRenderer = L.canvas({ padding: 0.5 });
    canvasRendererRef.current = canvasRenderer;

    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      attributionControl: true,
      preferCanvas: true,
    }).setView([59.3293, 18.0686], 10);

    // Public OpenStreetMap tile layer (reliable, no API key required)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    layerGroupRef.current = layerGroup;
    mapInstanceRef.current = map;

    // Zoom listener for dynamic zoom-aware scaling
    map.on('zoomend', () => {
      const z = map.getZoom();
      const currentValidStops = stopsRef.current.filter(
        (s) =>
          typeof s.latitude === 'number' &&
          typeof s.longitude === 'number' &&
          !isNaN(s.latitude) &&
          !isNaN(s.longitude) &&
          s.latitude !== 0 &&
          s.longitude !== 0
      );
      renderMarkers(currentValidStops, z, currentStopRef.current);
    });

    return () => {
      map.off('zoomend');
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
      canvasRendererRef.current = null;
    };
  }, [renderMarkers]);

  // Re-render markers on telemetry update or selection change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    renderMarkers(validStops, map.getZoom(), currentStopId);
  }, [validStops, currentStopId, renderMarkers]);

  // Fit bounds handler
  const handleFitBounds = () => {
    const map = mapInstanceRef.current;
    if (!map || validStops.length === 0) return;
    const bounds = L.latLngBounds(validStops.map((s) => [s.latitude, s.longitude]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14, animate: true });
  };

  const criticalCount = validStops.filter((s) => (s.highest_skip_probability ?? 0) >= 0.99).length;
  const highCount = validStops.filter((s) => {
    const p = s.highest_skip_probability ?? 0;
    return p >= 0.75 && p < 0.99;
  }).length;

  return (
    <div className="live-risk-map-wrapper">
      {/* Map Header */}
      <div className="map-header">
        <div className="map-title-group">
          <div className="map-title-row">
            <Map size={15} className="map-icon" />
            <span className="map-title">Live Risk Map</span>
          </div>
          <div className="map-meta-row">
            <span className="map-subtitle">
              {validStops.length.toLocaleString()} active stops with live telemetry
            </span>
            {(criticalCount > 0 || highCount > 0) && (
              <div className="map-alert-counts">
                {criticalCount > 0 && (
                  <span className="map-count-chip crit">{criticalCount} critical</span>
                )}
                {highCount > 0 && (
                  <span className="map-count-chip high">{highCount} high</span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="map-header-controls">
          <button
            type="button"
            className="fit-bounds-btn"
            onClick={handleFitBounds}
            disabled={validStops.length === 0}
            title="Reset map view to show all active stops"
          >
            <Maximize2 size={12} />
            Fit Active Stops
          </button>
        </div>
      </div>

      {/* Map Canvas */}
      <div className="map-canvas-container">
        <div ref={mapContainerRef} className="leaflet-canvas" />
        {validStops.length === 0 && (
          <div className="map-empty-overlay">
            <span>No active stops with live telemetry data available.</span>
          </div>
        )}
      </div>

      {/* Legend Bar */}
      <div className="map-legend-bar">
        <span className="legend-label">RISK LEVEL</span>
        <div className="legend-items">
          <div className="legend-item">
            <svg width="12" height="12" viewBox="0 0 12 12" className="legend-icon">
              <circle cx="6" cy="6" r="4.5" fill="#22c55e" fillOpacity="0.4" stroke="#14532d" strokeWidth="1" />
            </svg>
            <span>Low <span className="legend-range">(&lt;25%)</span></span>
          </div>
          <div className="legend-item">
            <svg width="12" height="12" viewBox="0 0 12 12" className="legend-icon">
              <circle cx="6" cy="6" r="5" fill="#f59e0b" fillOpacity="0.75" stroke="#78350f" strokeWidth="1" />
            </svg>
            <span>Moderate <span className="legend-range">(25–74%)</span></span>
          </div>
          <div className="legend-item">
            <svg width="14" height="14" viewBox="0 0 14 14" className="legend-icon">
              <circle cx="7" cy="7" r="5.5" fill="#f97316" fillOpacity="0.95" stroke="#431407" strokeWidth="1.5" />
            </svg>
            <span>High <span className="legend-range">(75–98%)</span></span>
          </div>
          <div className="legend-item">
            <svg width="16" height="16" viewBox="0 0 16 16" className="legend-icon">
              <circle cx="8" cy="8" r="7.5" fill="#ef4444" fillOpacity="0.22" />
              <circle cx="8" cy="8" r="5" fill="#ef4444" fillOpacity="0.95" stroke="#450a0a" strokeWidth="1.8" />
            </svg>
            <span>Critical <span className="legend-range">(≥99%)</span></span>
          </div>
        </div>
        <span className="legend-zoom-note">Zoom-scaled density hierarchy</span>
      </div>
    </div>
  );
}

// Popup HTML with risk badge, metadata and action
function buildPopupHtml(stop, level, formattedProb, riskLabel, routeShortName) {
  const badgeStyles = {
    critical: { bg: 'rgba(239,68,68,0.14)', border: 'rgba(239,68,68,0.3)', text: '#fca5a5', dot: '#ef4444' },
    high:     { bg: 'rgba(249,115,22,0.12)', border: 'rgba(249,115,22,0.28)', text: '#fdba74', dot: '#f97316' },
    medium:   { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.28)', text: '#fcd34d', dot: '#f59e0b' },
    low:      { bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.28)',  text: '#86efac', dot: '#22c55e' },
  };
  const b = badgeStyles[level] || badgeStyles.low;

  return `
    <div class="map-popup-card">
      <div class="popup-risk-hero" style="background:${b.bg};border-bottom:1px solid ${b.border}">
        <div class="popup-risk-pct" style="color:${b.text}">${formattedProb}</div>
        <div class="popup-risk-label" style="color:${b.text}">
          <span class="popup-risk-dot" style="background:${b.dot}"></span>
          ${riskLabel}
        </div>
      </div>
      <div class="popup-body">
        <div class="popup-title">${stop.stop_name}</div>
        <div class="popup-sub">Stop #${stop.stop_id}</div>
        <div class="popup-info-row">
          <span class="popup-info-key">Active trips</span>
          <span class="popup-info-val">${stop.prediction_count ?? 0}</span>
        </div>
        ${
          routeShortName
            ? `<div class="popup-info-row">
                <span class="popup-info-key">Top risk route</span>
                <span class="popup-info-val">Line ${routeShortName}</span>
              </div>`
            : ''
        }
      </div>
      <button type="button" class="popup-action-btn" id="popup-btn-${stop.stop_id}">
        Inspect Stop →
      </button>
    </div>
  `;
}

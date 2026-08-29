import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import StopSearch from './components/StopSearch';
import LiveActivityRadar from './components/LiveActivityRadar';
import RiskDistributionCard from './components/RiskDistributionCard';
import StopRiskDashboard from './components/StopRiskDashboard';
import LiveRiskMap from './components/LiveRiskMap';
import { EmptyStopState, LoadingState, ErrorState } from './components/UIStates';
import { getStopRisk, getLiveActivity } from './services/api';

export default function App() {
  const [selectedStop, setSelectedStop] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);

  // Live activity dataset state (used by Radar, Distribution, and Map)
  const [liveStops, setLiveStops] = useState([]);
  const [isLiveLoading, setIsLiveLoading] = useState(true);
  const [isLiveRefreshing, setIsLiveRefreshing] = useState(false);
  const [liveError, setLiveError] = useState(null);

  // 1. Fetch live activity dataset (limit=0 for all active stops)
  const fetchLiveActivity = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      setIsLiveLoading(true);
      setLiveError(null);
    } else {
      setIsLiveRefreshing(true);
    }

    try {
      const data = await getLiveActivity(0);
      setLiveStops(data.stops || []);
      setLiveError(null);
    } catch (err) {
      console.error('Failed to fetch live activity:', err);
      if (!isBackground) {
        setLiveError(err.message || 'Failed to fetch live activity telemetry.');
      }
    } finally {
      setIsLiveLoading(false);
      setIsLiveRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchLiveActivity(false);
    const intervalId = setInterval(() => {
      fetchLiveActivity(true);
    }, 20000);
    return () => clearInterval(intervalId);
  }, [fetchLiveActivity]);

  // 2. Fetch targeted stop risk data when a stop is selected
  const fetchRiskForStop = useCallback(async (stopId, isBackground = false) => {
    if (!stopId) return;

    if (!isBackground) {
      setIsLoading(true);
      setError(null);
    } else {
      setIsRefreshing(true);
    }

    try {
      const data = await getStopRisk(stopId);
      setRiskData(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch stop risk:', err);
      if (!isBackground) {
        setError(err.message || 'Failed to connect to GhostBus AI API backend.');
        setRiskData(null);
      }
    } finally {
      if (!isBackground) {
        setIsLoading(false);
      }
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedStop?.stop_id) {
      setRiskData(null);
      setLastUpdated(null);
      return;
    }

    fetchRiskForStop(selectedStop.stop_id, false);

    const intervalId = setInterval(() => {
      fetchRiskForStop(selectedStop.stop_id, true);
    }, 20000);

    return () => clearInterval(intervalId);
  }, [selectedStop, fetchRiskForStop]);

  const handleSelectStop = (stop) => {
    setSelectedStop(stop);
  };

  const handleManualRefreshStop = () => {
    if (selectedStop?.stop_id) {
      fetchRiskForStop(selectedStop.stop_id, riskData !== null);
    }
  };

  return (
    <div className="app-container">
      <Header />

      <main>
        <StopSearch onSelectStop={handleSelectStop} currentStop={selectedStop} />

        {/* Upper 2-Column Dashboard Grid */}
        <div className="upper-dashboard-grid">
          {/* Left Column: System Overview (Radar + Risk Distribution) */}
          <div className="dashboard-left-col">
            <LiveActivityRadar
              stops={liveStops}
              isLoading={isLiveLoading}
              isRefreshing={isLiveRefreshing}
              error={liveError}
              onSelectStop={handleSelectStop}
              currentStopId={selectedStop?.stop_id}
              onRefreshLive={() => fetchLiveActivity(liveStops.length > 0)}
            />
            <RiskDistributionCard stops={liveStops} isLoading={isLiveLoading} />
          </div>

          {/* Right Column: Persistent Fixed-Height Current Stop Panel */}
          <div className="dashboard-right-col stop-panel-container">
            {isLoading ? (
              <LoadingState stopName={selectedStop?.stop_name} />
            ) : error && !riskData ? (
              <ErrorState message={error} onRetry={handleManualRefreshStop} />
            ) : riskData ? (
              <StopRiskDashboard
                data={riskData}
                lastUpdated={lastUpdated}
                isRefreshing={isRefreshing}
                onRefresh={handleManualRefreshStop}
              />
            ) : (
              <EmptyStopState />
            )}
          </div>
        </div>

        {/* Full-Width Live Risk Map Below Grid */}
        <LiveRiskMap
          stops={liveStops}
          onSelectStop={handleSelectStop}
          currentStopId={selectedStop?.stop_id}
        />
      </main>
    </div>
  );
}

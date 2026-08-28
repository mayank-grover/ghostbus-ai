import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import StopSearch from './components/StopSearch';
import StopRiskDashboard from './components/StopRiskDashboard';
import { InitialState, LoadingState, ErrorState } from './components/UIStates';
import { getStopRisk } from './services/api';

export default function App() {
  const [selectedStop, setSelectedStop] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState(null);

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
      // Only show full error screen if we don't have risk data yet
      if (!isBackground) {
        setError(err.message || 'Failed to connect to GhostBus AI API backend.');
        setRiskData(null);
      }
      // Background failure preserves existing riskData silently
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

    // 1. Immediate fetch when stop is selected
    fetchRiskForStop(selectedStop.stop_id, false);

    // 2. Set up 20-second automatic background refresh
    const intervalId = setInterval(() => {
      fetchRiskForStop(selectedStop.stop_id, true);
    }, 20000);

    // 3. Cleanup interval on stop change or unmount
    return () => clearInterval(intervalId);
  }, [selectedStop, fetchRiskForStop]);

  const handleSelectStop = (stop) => {
    setSelectedStop(stop);
  };

  const handleManualRefresh = () => {
    if (selectedStop?.stop_id) {
      fetchRiskForStop(selectedStop.stop_id, riskData !== null);
    }
  };

  return (
    <div className="app-container">
      <Header />

      <main>
        <StopSearch onSelectStop={handleSelectStop} currentStop={selectedStop} />

        {isLoading ? (
          <LoadingState stopName={selectedStop?.stop_name} />
        ) : error && !riskData ? (
          <ErrorState message={error} onRetry={handleManualRefresh} />
        ) : riskData ? (
          <StopRiskDashboard
            data={riskData}
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            onRefresh={handleManualRefresh}
          />
        ) : (
          <InitialState />
        )}
      </main>
    </div>
  );
}

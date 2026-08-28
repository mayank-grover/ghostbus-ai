const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

/**
 * Search bus stops by name query.
 * Calls GET /api/v1/stops/search?q=<query>
 */
export async function searchStops(query) {
  if (!query || !query.trim()) {
    return [];
  }

  const url = `${API_BASE_URL}/stops/search?q=${encodeURIComponent(query.trim())}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Search failed with status ${response.status}`);
  }

  const data = await response.json();
  return data.stops || [];
}

/**
 * Fetch live skip risk summary for a stop.
 * Calls GET /api/v1/stops/{stop_id}/risk
 */
export async function getStopRisk(stopId) {
  if (!stopId) {
    throw new Error('Stop ID is required');
  }

  const url = `${API_BASE_URL}/stops/${encodeURIComponent(stopId)}/risk`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch risk data for stop ${stopId}`);
  }

  return await response.json();
}

/**
 * Fetch top active high-risk stops across current live trips.
 * Calls GET /api/v1/live-activity?limit=<limit>
 */
export async function getLiveActivity(limit = 20) {
  const url = `${API_BASE_URL}/live-activity?limit=${encodeURIComponent(limit)}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch live activity with status ${response.status}`);
  }

  return await response.json();
}

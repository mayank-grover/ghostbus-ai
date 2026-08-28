/**
 * Format delay in seconds into a human-readable text string.
 * e.g., 240 => "+4 min delay"
 *       0   => "On time"
 *      -60  => "1 min early"
 */
export function formatDelay(seconds) {
  if (seconds === undefined || seconds === null || isNaN(seconds)) {
    return 'No delay data';
  }

  const sec = Number(seconds);
  if (Math.abs(sec) < 30) {
    return 'On time';
  }

  const mins = Math.round(Math.abs(sec) / 60);

  if (sec > 0) {
    return mins === 1 ? '+1 min delay' : `+${mins} min delay`;
  } else {
    return mins === 1 ? '1 min early' : `${mins} min early`;
  }
}

/**
 * Format a probability float (0.0 - 1.0) into a clean percentage string.
 */
export function formatProbability(prob) {
  if (prob === undefined || prob === null || isNaN(prob)) {
    return '0.0%';
  }
  const percentage = Number(prob) * 100;
  return `${percentage.toFixed(1)}%`;
}

/**
 * Determine risk level category ('high' | 'medium' | 'low')
 */
export function getRiskLevel(prob) {
  const p = Number(prob) || 0;
  if (p >= 0.70) return 'high';
  if (p >= 0.35) return 'medium';
  return 'low';
}

/**
 * Human-readable risk label
 */
export function getRiskLabel(prob) {
  const level = getRiskLevel(prob);
  if (level === 'high') return 'High Skip Risk';
  if (level === 'medium') return 'Moderate Risk';
  return 'Low Risk';
}

export const RISK_COLORS = {
  Low: '#4ade80',
  Medium: '#fbbf24',
  High: '#fb923c',
  Critical: '#ef4444',
}

export function getRiskColor(riskLevel) {
  return RISK_COLORS[riskLevel] ?? '#b8b4c2'
}

export function getRiskClass(riskLevel) {
  const normalized = (riskLevel ?? '').toLowerCase()
  if (normalized === 'low') return 'risk-low'
  if (normalized === 'medium') return 'risk-medium'
  if (normalized === 'high') return 'risk-high'
  if (normalized === 'critical') return 'risk-critical'
  return 'risk-unknown'
}

export function isMediumPlusRisk(riskLevel) {
  return ['Medium', 'High', 'Critical'].includes(riskLevel)
}

export function buildMitigationMap(mitigations = []) {
  return Object.fromEntries(mitigations.map((entry) => [entry.node_id, entry]))
}

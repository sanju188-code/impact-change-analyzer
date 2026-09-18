import { getRiskClass, isMediumPlusRisk } from '../utils/risk'

export default function ComponentCard({ component, mitigation }) {
  const incidents = component.related_incidents ?? []
  const showMitigation = isMediumPlusRisk(component.risk_level) && mitigation?.suggestion

  return (
    <article className="component-card">
      <div className="component-card__header">
        <div className="component-card__identity">
          <h3 className="component-card__title">{component.node_id}</h3>
          <p className="component-card__path">{component.path}</p>
        </div>
        <div className="component-card__badges">
          <span className={`evidence-badge evidence-badge--${component.evidence_strength}`}>
            {component.evidence_strength === 'confirmed' ? '📋 Confirmed' : '⚠️ Inferred'}
          </span>
          <span className={`risk-badge ${getRiskClass(component.risk_level)}`}>
            {component.risk_level}
          </span>
        </div>
      </div>

      <p className="component-card__explanation">{component.explanation}</p>

      {showMitigation && (
        <p className="component-card__mitigation">
          <span className="component-card__mitigation-label">💡 Suggested mitigation:</span>{' '}
          {mitigation.suggestion}
        </p>
      )}

      {incidents.length > 0 && (
        <div className="component-card__incidents">
          {incidents.map((incident) => (
            <span key={incident} className="incident-tag">
              {incident}
            </span>
          ))}
        </div>
      )}
    </article>
  )
}

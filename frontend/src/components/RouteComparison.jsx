import { LEVEL_COLORS } from './common'

const ROLES = [['safest', 'Safest Route'], ['balanced', 'Balanced Route'], ['fastest', 'Fastest Route']]

export default function RouteComparison({ analysis, routeIndex, setRouteIndex }) {
  if (!analysis) return null
  const { comparison, routes } = analysis
  return (
    <div className="compare">
      <h4>Route Comparison</h4>
      {ROLES.map(([k, t]) => {
        const i = comparison[k]
        if (i == null) return (
          <div className="cmp-card empty" key={k}><b>{t}</b><span className="muted">Not available — OSRM returned only {routes.length} route{routes.length > 1 ? 's' : ''}</span></div>
        )
        const s = routes[i].summary
        const also = ROLES.filter(([k2]) => k2 !== k && comparison[k2] === i).map(([, t2]) => t2)
        return (
          <div key={k} className={`cmp-card ${i === routeIndex ? 'active' : ''}`} onClick={() => setRouteIndex(i)}>
            <div className="cmp-head"><b>{t}</b>{also.length > 0 && <small>also: {also.join(', ')}</small>}</div>
            <div className="cmp-grid">
              <span>{s.distance_mi} mi</span>
              <span>Estimated Time: {s.estimated_time_min} min</span>
              <span style={{ color: LEVEL_COLORS[s.risk_level], fontWeight: 700 }}>{s.risk_score}/100 · {s.risk_level}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

import { LEVEL_COLORS } from './common'
import RouteComparison from './RouteComparison'
import SHAPPanel from './SHAPPanel'

export default function RouteRiskAnalysis({ analysis, routeIndex, setRouteIndex, selectedSegment, shap, shapLoading, shapScope }) {
  if (!analysis) {
    return (
      <aside className="right">
        <section className="card"><h3>Route Risk Analysis</h3>
          <p className="muted">Enter a start and destination in San Diego, then press <b>Generate Routes</b>.</p></section>
        <SHAPPanel shap={null} />
      </aside>
    )
  }
  const r = analysis.routes[routeIndex]
  const s = r.summary
  const seg = selectedSegment || r.segments.find((x) => x.id === s.highest_risk_segment.id)
  return (
    <aside className="right">
      <section className="card">
        <h3>Route Risk Analysis</h3>
        <div className="big-score" style={{ color: LEVEL_COLORS[s.risk_level] }}>{s.risk_score}<small>/100</small></div>
        <div className="big-level" style={{ background: LEVEL_COLORS[s.risk_level] }}>{s.risk_level} Risk</div>
        <p className="muted small center">Predicted Accident Risk (historical)</p>
        <dl className="stats">
          <dt>Number of Road Segments</dt><dd>{s.n_segments}</dd>
          <dt>High-Risk Segments</dt><dd>{s.high_risk_segments}</dd>
          <dt>Critical-Risk Segments</dt><dd>{s.critical_risk_segments}</dd>
          <dt>Average Segment Risk</dt><dd>{s.average_segment_risk}</dd>
          <dt>Highest-Risk Segment</dt><dd>{s.highest_risk_segment.id} ({s.highest_risk_segment.risk_score})</dd>
          <dt>Segments with matched history</dt><dd>{s.segments_with_history}/{s.n_segments}</dd>
        </dl>
        <h4>Route Summary</h4>
        <dl className="stats">
          <dt>Distance</dt><dd>{s.distance_mi} mi ({s.distance_km} km)</dd>
          <dt>Estimated Time</dt><dd>{s.estimated_time_min} min</dd>
          <dt>Route Risk</dt><dd>{s.risk_score} · {s.risk_level}</dd>
        </dl>
        <RouteComparison analysis={analysis} routeIndex={routeIndex} setRouteIndex={setRouteIndex} />
      </section>

      <section className="card">
        <h3>AI Road Risk Analysis</h3>
        <h4>Road Segment {selectedSegment ? '' : '(highest risk)'}</h4>
        <dl className="stats">
          <dt>Segment ID</dt><dd>{seg.id}</dd>
          <dt>Road Name</dt><dd>{seg.road_name}</dd>
          <dt>Location</dt><dd>{seg.location.lat.toFixed(4)}, {seg.location.lng.toFixed(4)}</dd>
          <dt>Risk Score</dt><dd>{seg.risk_score}</dd>
          <dt>Risk Level</dt><dd style={{ color: LEVEL_COLORS[seg.risk_level], fontWeight: 700 }}>{seg.risk_level}</dd>
          <dt>Historical accidents nearby</dt><dd>{seg.accidents_nearby}{seg.match_radius_m ? ` (within ${seg.match_radius_m} m)` : ' — none found'}</dd>
          <dt>Predicted severity class</dt><dd>{seg.predicted_severity}</dd>
        </dl>
        {!seg.has_history && <p className="warn small">No historical accidents matched this segment; its score reflects default road features only.</p>}
      </section>

      <SHAPPanel shap={shap} loading={shapLoading} scopeLabel={shapScope} />
      <p className="disclaimer">{analysis.disclaimer}</p>
    </aside>
  )
}

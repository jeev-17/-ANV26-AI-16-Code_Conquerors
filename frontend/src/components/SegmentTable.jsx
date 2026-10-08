import { LEVEL_BG, LEVEL_COLORS } from './common'

export default function SegmentTable({ segments, selectedId, onSelect, layers }) {
  const rows = (segments || []).filter((s) => layers.all || layers[s.risk_level])
  return (
    <section className="card table-card">
      <h3>Route Segments</h3>
      <div className="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Segment ID</th><th>Road Name</th><th>From → To</th><th>Risk Score</th><th>Risk Level</th></tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={6} className="muted">No segments to display yet.</td></tr>}
            {rows.map((s) => (
              <tr key={s.id} className={s.id === selectedId ? 'sel' : ''} onClick={() => onSelect(s.id)}>
                <td>{s.index}</td><td>{s.id}</td><td>{s.road_name}</td><td>{s.from_to}</td>
                <td><b>{s.risk_score}</b></td>
                <td><span className="badge" style={{ background: LEVEL_BG[s.risk_level], color: LEVEL_COLORS[s.risk_level] }}>{s.risk_level}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

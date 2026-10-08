import { LEVEL_COLORS } from './common'

const ITEMS = [['Low', 'Low Risk (0–25)'], ['Moderate', 'Moderate Risk (26–50)'],
  ['High', 'High Risk (51–75)'], ['Critical', 'Critical Risk (76–100)']]

export default function RiskLegend() {
  return (
    <section className="card">
      <h3>Risk Legend</h3>
      {ITEMS.map(([k, t]) => (
        <div className="legend-row" key={k}><i style={{ background: LEVEL_COLORS[k] }} />{t}</div>
      ))}
    </section>
  )
}

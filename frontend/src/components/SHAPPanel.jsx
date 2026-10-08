export default function SHAPPanel({ shap, loading, scopeLabel }) {
  if (loading) return <section className="card"><h3>Top Contributing Factors (SHAP)</h3><p className="muted">Computing SHAP values…</p></section>
  if (!shap) return <section className="card"><h3>Top Contributing Factors (SHAP)</h3><p className="muted">Generate a route to see explanations.</p></section>
  const max = Math.max(...shap.factors.map((f) => Math.abs(f.shap_value)), 1e-9)
  return (
    <section className="card">
      <h3>Top Contributing Factors (SHAP)</h3>
      <p className="muted small">{scopeLabel} · {shap.units}</p>
      {shap.factors.map((f) => (
        <div className="shap-row" key={f.feature}>
          <div className="shap-label">{f.label}{f.value != null && <small> = {String(f.value)}</small>}</div>
          <div className="shap-bar-wrap">
            <div className={`shap-bar ${f.shap_value > 0 ? 'up' : 'down'}`} style={{ width: `${(Math.abs(f.shap_value) / max) * 100}%` }} />
          </div>
          <div className="shap-val">{f.shap_value > 0 ? '+' : ''}{f.shap_value.toFixed(3)}</div>
        </div>
      ))}
      <p className="muted small"><span className="dot up" /> increases predicted risk &nbsp; <span className="dot down" /> decreases predicted risk</p>
    </section>
  )
}

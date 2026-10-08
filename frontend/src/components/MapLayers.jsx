export default function MapLayers({ layers, setLayers }) {
  const set = (k) => (e) => setLayers({ ...layers, [k]: e.target.checked })
  return (
    <section className="card">
      <h3>Map Layers</h3>
      <label className="check"><input type="checkbox" checked={layers.all} onChange={set('all')} /> All Roads</label>
      <label className="check"><input type="checkbox" checked={layers.Moderate} onChange={set('Moderate')} disabled={layers.all} /> Moderate Risk</label>
      <label className="check"><input type="checkbox" checked={layers.High} onChange={set('High')} disabled={layers.all} /> High Risk</label>
      <label className="check"><input type="checkbox" checked={layers.Critical} onChange={set('Critical')} disabled={layers.all} /> Critical Risk</label>
    </section>
  )
}

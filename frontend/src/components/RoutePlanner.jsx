const OPTIONS = [['safest', 'Safest Route'], ['balanced', 'Balanced Route'], ['fastest', 'Fastest Route']]

export default function RoutePlanner({ start, end, setStart, setEnd, option, setOption, onGenerate, loading, comparison }) {
  return (
    <section className="card">
      <h3>Plan Your Route</h3>
      <label className="field">Start Location
        <input value={start} onChange={(e) => setStart(e.target.value)} placeholder="e.g. San Diego Airport" />
      </label>
      <label className="field">Destination
        <input value={end} onChange={(e) => setEnd(e.target.value)} placeholder="e.g. Balboa Park" />
      </label>
      <h4>Route Options</h4>
      {OPTIONS.map(([k, t]) => {
        const unavailable = comparison && comparison[k] == null
        return (
          <label key={k} className={`radio ${unavailable ? 'disabled' : ''}`}>
            <input type="radio" name="opt" checked={option === k} disabled={unavailable} onChange={() => setOption(k)} />
            {t}{unavailable ? ' (not available)' : ''}
          </label>
        )
      })}
      <button className="primary" onClick={onGenerate} disabled={loading || !start.trim() || !end.trim()}>
        {loading ? 'Analyzing…' : 'Generate Routes'}
      </button>
    </section>
  )
}

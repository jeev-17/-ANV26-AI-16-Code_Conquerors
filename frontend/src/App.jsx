import { useEffect, useState } from 'react'
import Navbar from './components/Navbar'
import RoutePlanner from './components/RoutePlanner'
import RiskLegend from './components/RiskLegend'
import MapLayers from './components/MapLayers'
import MapView from './components/MapView'
import SegmentTable from './components/SegmentTable'
import RouteRiskAnalysis from './components/RouteRiskAnalysis'
import { explain, getRouteRisk } from './services/api'

export default function App() {
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [option, setOption] = useState('safest')
  const [analysis, setAnalysis] = useState(null)
  const [routeIndex, setRouteIndex] = useState(0)
  const [selectedId, setSelectedId] = useState(null)
  const [layers, setLayers] = useState({ all: true, Moderate: false, High: false, Critical: false })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [shap, setShap] = useState(null)
  const [shapLoading, setShapLoading] = useState(false)

  const generate = async () => {
    setLoading(true); setError(null); setSelectedId(null); setShap(null)
    try {
      const a = await getRouteRisk(start.trim(), end.trim())
      setAnalysis(a)
      const idx = a.comparison[option] ?? a.comparison.safest
      setRouteIndex(idx)
    } catch (e) { setError(e.message); setAnalysis(null) } finally { setLoading(false) }
  }

  // radio option -> route index
  useEffect(() => {
    if (analysis && analysis.comparison[option] != null) { setRouteIndex(analysis.comparison[option]); setSelectedId(null) }
  }, [option]) // eslint-disable-line

  // fetch real SHAP values for route / segment
  useEffect(() => {
    if (!analysis) return
    let cancelled = false
    setShapLoading(true)
    explain(analysis.analysis_id, routeIndex, selectedId)
      .then((d) => { if (!cancelled) setShap(d) })
      .catch((e) => { if (!cancelled) { setShap(null); setError(e.message) } })
      .finally(() => { if (!cancelled) setShapLoading(false) })
    return () => { cancelled = true }
  }, [analysis, routeIndex, selectedId])

  const route = analysis?.routes[routeIndex]
  const selectedSegment = route?.segments.find((s) => s.id === selectedId) || null

  return (
    <div className="app">
      <Navbar />
      {error && <div className="error" onClick={() => setError(null)}>⚠ {error} <small>(click to dismiss)</small></div>}
      <div className="layout">
        <aside className="left">
          <RoutePlanner {...{ start, end, setStart, setEnd, option, setOption, loading }}
            onGenerate={generate} comparison={analysis?.comparison} />
          <RiskLegend />
          <MapLayers layers={layers} setLayers={setLayers} />
        </aside>
        <main className="center">
          <MapView analysis={analysis} routeIndex={routeIndex} setRouteIndex={(i) => { setRouteIndex(i); setSelectedId(null) }}
            layers={layers} selectedId={selectedId} onSelectSegment={setSelectedId} />
          <SegmentTable segments={route?.segments} selectedId={selectedId} onSelect={setSelectedId} layers={layers} />
        </main>
        <RouteRiskAnalysis analysis={analysis} routeIndex={routeIndex}
          setRouteIndex={(i) => { setRouteIndex(i); setSelectedId(null) }}
          selectedSegment={selectedSegment} shap={shap} shapLoading={shapLoading}
          shapScope={selectedSegment ? `Segment ${selectedSegment.id}` : 'Whole route'} />
      </div>
    </div>
  )
}

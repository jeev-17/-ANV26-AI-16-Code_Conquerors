import { useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { LEVEL_COLORS } from './common'

const pin = (t, c) => L.divIcon({
  className: '', iconSize: [30, 30], iconAnchor: [15, 15],
  html: `<div class="pin" style="background:${c}">${t}</div>`,
})

function Fit({ path }) {
  const map = useMap()
  useEffect(() => { if (path?.length) map.fitBounds(path, { padding: [40, 40] }) }, [path, map])
  return null
}

export default function MapView({ analysis, routeIndex, setRouteIndex, layers, selectedId, onSelectSegment }) {
  const route = analysis?.routes[routeIndex]
  const visible = (lvl) => layers.all || layers[lvl]
  return (
    <MapContainer center={[32.7157, -117.1611]} zoom={11} className="map" scrollWheelZoom>
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {analysis && analysis.routes.map((r, i) => i !== routeIndex && (
        <Polyline key={`alt${i}`} positions={r.path} pathOptions={{ color: '#64748b', weight: 4, dashArray: '8 8', opacity: 0.7 }}
          eventHandlers={{ click: () => setRouteIndex(i) }}>
          <Popup>Alternative route {i + 1} — click to select</Popup>
        </Polyline>
      ))}
      {route && route.segments.filter((s) => visible(s.risk_level)).map((s) => (
        <Polyline key={s.id} positions={s.coords}
          pathOptions={{ color: LEVEL_COLORS[s.risk_level], weight: s.id === selectedId ? 10 : 6, opacity: 0.95 }}
          eventHandlers={{ click: () => onSelectSegment(s.id) }}>
          <Popup>
            <b>{s.road_name}</b><br />Risk {s.risk_score}/100 ({s.risk_level})<br />
            Historical accidents nearby: {s.accidents_nearby}
          </Popup>
        </Polyline>
      ))}
      {analysis && <>
        <Marker position={[analysis.start.lat, analysis.start.lng]} icon={pin('A', '#2563eb')}><Popup>Start: {analysis.start.display_name}</Popup></Marker>
        <Marker position={[analysis.end.lat, analysis.end.lng]} icon={pin('B', '#7c3aed')}><Popup>Destination: {analysis.end.display_name}</Popup></Marker>
        <Fit path={route?.path} />
      </>}
    </MapContainer>
  )
}

import { useState } from 'react'

export default function Navbar() {
  const [open, setOpen] = useState(false)
  return (
    <header className="navbar">
      <div className="brand">
        <span className="logo">🛡️</span>
        <span className="brand-name">Safe<b>Route</b>AI</span>
      </div>
      <nav className="nav-tags">
        <span>AI-Powered Route Analysis</span>
        <span>Historical Accident Data</span>
        <span>Explainable Insights</span>
      </nav>
      <div className="nav-right">
        <span className="city">📍 San Diego, CA</span>
        <button className="icon-btn" onClick={() => setOpen(!open)} aria-label="Information">ⓘ</button>
        {open && (
          <div className="info-pop">
            <p><b>Predicted / Historical Accident Risk.</b> Risk predictions are generated from historical accident data and are intended for research and demonstration purposes. Predictions indicate estimated historical accident risk and should not be interpreted as guaranteed accident probability or a substitute for safe driving.</p>
            <p>Routing times are estimates and are not based on live traffic.</p>
          </div>
        )}
      </div>
    </header>
  )
}

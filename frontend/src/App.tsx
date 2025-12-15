import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [health, setHealth] = useState<string>('checking...')

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(data => setHealth(data.status))
      .catch(() => setHealth('error'))
  }, [])

  return (
    <div className="App">
      <h1>ATC - Automated Team Collaboration</h1>
      <p>Backend Status: {health}</p>
    </div>
  )
}

export default App

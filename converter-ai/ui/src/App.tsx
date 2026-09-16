import { useState } from 'react'
import './App.css'

function App() {
  const [url, setUrl] = useState('')

  const handleMigrate = () => {
    console.log('Migrate clicked with URL:', url)
  }

  return (
    <div className="page">
      <div className="card">
        <h1> Migrator</h1>
        <div className="form-row">
          <input
            type="url"
            className="url-input"
            placeholder=""
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            type="button"
            className="migrate-button"
            onClick={handleMigrate}
            disabled={!url}
          >
            Migrate
          </button>
        </div>
      </div>
    </div>
  )
}

export default App

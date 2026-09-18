import { useState } from 'react'
import './App.css'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

type MigrateResult = {
  job_id: string
  files: { file: string; status: string }[]
  download_url: string
}

function App() {
  const [url, setUrl] = useState('https://github.com/abhijithss2010/sample-vue-app')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MigrateResult | null>(null)

  const handleMigrate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${API_BASE}/api/migrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: url }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Migration failed')
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Migration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="card">
        <h1>Migrator</h1>
        <p className="subtitle">Vue 3 to React migration, powered by Claude</p>
        <div className="form-row">
          <input
            type="url"
            className="url-input"
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button
            type="button"
            className="migrate-button"
            onClick={handleMigrate}
            disabled={!url || loading}
          >
            {loading ? 'Migrating...' : 'Migrate'}
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        {result && (
          <div className="result">
            <p>
              Migrated {result.files.length} file(s).
            </p>
            <ul className="file-list">
              {result.files.map((f) => (
                <li key={f.file}>
                  {f.file} — {f.status}
                </li>
              ))}
            </ul>
            <a
              className="download-link"
              href={`${API_BASE}${result.download_url}`}
            >
              Download migrated project (.zip)
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

export default App

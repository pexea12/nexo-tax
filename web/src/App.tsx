import { useState } from 'react'
import FileUpload from './components/FileUpload'
import YearSelector from './components/YearSelector'
import ResultsView from './components/ResultsView'
import DownloadLinks from './components/DownloadLinks'
import FeedbackForm from './components/FeedbackForm'
import Footer from './components/Footer'
import InfoSection from './components/InfoSection'
import { trackEvent } from './hooks/usePlausible'
import { usePyodide } from './hooks/usePyodide'
import { DetectedYears, YearResult } from './types'
import './App.css'

function App() {
  const { loading: pyodideLoading, error: pyodideError, runCalculation } = usePyodide()
  const [files, setFiles] = useState<File[]>([])
  const [detectedYears, setDetectedYears] = useState<DetectedYears>({})
  const [yearResults, setYearResults] = useState<YearResult[]>([])
  const [calcError, setCalcError] = useState('')
  const [auditFiles, setAuditFiles] = useState<Record<string, string>>({})
  const [isCalculating, setIsCalculating] = useState(false)
  const [useAuditCsv, setUseAuditCsv] = useState(false)

  const detectYearsFromFiles = async (files: File[]) => {
    const years: Set<number> = new Set()

    for (const file of files) {
      const text = await file.text()
      const lines = text.split('\n')

      // Find Date / Time column index
      const headerLine = lines[0]
      const headers = headerLine.split(',')
      const dateColIndex = headers.findIndex((h) => h.includes('Date / Time (UTC)'))

      if (dateColIndex !== -1) {
        // Parse dates from CSV
        for (let i = 1; i < lines.length; i++) {
          if (!lines[i].trim()) continue
          const cells = lines[i].split(',')
          if (cells[dateColIndex]) {
            const dateStr = cells[dateColIndex]
            const match = dateStr.match(/(\d{4})-/)
            if (match) {
              years.add(parseInt(match[1]))
            }
          }
        }
      }
    }

    // Initialize all detected years as checked
    const yearObj: DetectedYears = {}
    Array.from(years)
      .sort()
      .forEach((year) => {
        yearObj[year] = true
      })

    setDetectedYears(yearObj)
  }

  const handleFilesSelected = async (selectedFiles: File[]) => {
    setFiles(selectedFiles)
    setYearResults([])
    setCalcError('')
    setAuditFiles({})
    await detectYearsFromFiles(selectedFiles)
  }

  const handleCalculate = async () => {
    const selectedYears = Object.entries(detectedYears)
      .filter(([_, selected]) => selected)
      .map(([year]) => parseInt(year))

    if (selectedYears.length === 0) {
      alert('Please select at least one year')
      return
    }

    setIsCalculating(true)
    trackEvent('Calculate Tax', { years: selectedYears.join(','), files: files.length })
    try {
      // Read CSV contents
      const csvContents = await Promise.all(files.map((f) => f.text()))

      // Run calculation
      const result = await runCalculation(csvContents, selectedYears, useAuditCsv)

      setYearResults(result.years ?? [])
      setAuditFiles(result.audit_files ?? {})
      setCalcError('')
      trackEvent('Calculation Success', { years: selectedYears.join(',') })
    } catch (err) {
      setCalcError(err instanceof Error ? err.message : String(err))
      setYearResults([])
      trackEvent('Calculation Error')
    } finally {
      setIsCalculating(false)
    }
  }

  return (
    <div className="app-container">
      <header>
        <h1>Nexo Tax Calculator</h1>
        <p>Calculate your Finnish crypto tax from Nexo transactions</p>
        {pyodideLoading && <div style={{ color: '#ffd700' }}>Loading calculator...</div>}
        {pyodideError && <div style={{ color: '#ff6b6b' }}>Error: {pyodideError}</div>}
        <div style={{ fontSize: '0.85em', color: '#999', marginTop: '0.5rem' }}>
          <span aria-hidden="true">🔒</span> Your files never leave your browser. All calculations run locally.
        </div>
      </header>

      <main>
        <InfoSection />

        <FileUpload
          onFilesSelected={handleFilesSelected}
          disabled={pyodideLoading || isCalculating}
        />

        {files.length > 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            <p>
              <strong>{files.length}</strong> file{files.length !== 1 ? 's' : ''} selected:{' '}
              {files.map((f) => f.name).join(', ')}
            </p>
          </div>
        )}

        {Object.keys(detectedYears).length > 0 && (
          <>
            <YearSelector
              years={detectedYears}
              onYearsChange={setDetectedYears}
              disabled={pyodideLoading || isCalculating}
            />

            <div style={{ marginTop: '1rem' }}>
              <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', justifyContent: 'center' }}>
                <input
                  type="checkbox"
                  checked={useAuditCsv}
                  onChange={(e) => setUseAuditCsv(e.target.checked)}
                  disabled={pyodideLoading || isCalculating}
                />
                Generate audit CSV files
              </label>
            </div>

            <div style={{ marginTop: '1.5rem' }}>
              <button
                onClick={handleCalculate}
                disabled={pyodideLoading || isCalculating}
                style={{
                  padding: '0.75rem 2rem',
                  fontSize: '1.1em',
                  fontWeight: 'bold',
                }}
              >
                {isCalculating ? 'Calculating...' : 'Calculate Tax'}
              </button>
            </div>
          </>
        )}

        {calcError && (
          <div style={{ marginTop: '1.5rem', color: '#f44336', background: '#1a0000', border: '1px solid #500', borderRadius: '6px', padding: '1rem', textAlign: 'left' }}>
            <strong>Error:</strong> {calcError}
          </div>
        )}
        {isCalculating && (
          <div style={{ marginTop: '1.5rem', color: '#ffd700' }}>Calculating...</div>
        )}
        <ResultsView years={yearResults} />

        {Object.keys(auditFiles).length > 0 && (
          <DownloadLinks files={auditFiles} disabled={isCalculating} />
        )}

        <FeedbackForm />
      </main>

      <Footer />
    </div>
  )
}

export default App

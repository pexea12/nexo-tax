import { useEffect, useState, useCallback } from 'react'
import { CalculationResult } from '../types'

declare global {
  interface Window {
    loadPyodide?: () => Promise<any>
  }
}

export function usePyodide() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pyodide, setPyodide] = useState<any | null>(null)

  useEffect(() => {
    const initPyodide = async () => {
      try {
        // Load Pyodide script
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/pyodide/v0.24.0/full/pyodide.js'
        script.onload = async () => {
          const py = await (window as any).loadPyodide()

          // Mount nexo_tax package from dist
          await py.runPythonAsync(`
import sys
sys.path.insert(0, '/nexo_tax')
          `)

          setPyodide(py)
          setLoading(false)
        }
        script.onerror = () => {
          setError('Failed to load Pyodide from CDN')
          setLoading(false)
        }
        document.head.appendChild(script)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to initialize Pyodide')
        setLoading(false)
      }
    }

    initPyodide()
  }, [])

  const runCalculation = useCallback(
    async (csvContents: string[], years: number[], auditCsv: boolean): Promise<CalculationResult> => {
      if (!pyodide) {
        throw new Error('Pyodide not loaded')
      }

      try {
        // Convert JS arrays to Python
        const pyYears = pyodide.toPy(years)
        const pyCsvContents = pyodide.toPy(csvContents)
        const pyAuditCsv = pyodide.toPy(auditCsv)

        // Call the API
        const result = await pyodide.runPythonAsync(`
from nexo_tax.api import run

result = run(${pyCsvContents}, ${pyYears}, ${pyAuditCsv})
result
        `)

        // Convert Python dict to JS object
        return pyodide.toPy(result).toJs()
      } catch (err) {
        throw new Error(`Calculation failed: ${err instanceof Error ? err.message : String(err)}`)
      }
    },
    [pyodide]
  )

  return { loading, error, pyodide, runCalculation }
}

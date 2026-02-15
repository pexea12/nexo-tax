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
          try {
          const py = await (window as any).loadPyodide()

          // Fetch and write nexo_tax package files into Pyodide's virtual filesystem
          const packageFiles = [
            '__init__.py',
            'api.py',
            'calculator.py',
            'fx.py',
            'models.py',
            'parser.py',
            'report.py',
            'cli/__init__.py',
            'cli/main.py',
          ]
          py.FS.mkdir('/nexo_tax')
          py.FS.mkdir('/nexo_tax/cli')
          for (const file of packageFiles) {
            const resp = await fetch(`/nexo_tax/${file}`)
            if (!resp.ok) {
              throw new Error(`Failed to fetch /nexo_tax/${file}: ${resp.status} ${resp.statusText}`)
            }
            const text = await resp.text()
            py.FS.writeFile(`/nexo_tax/${file}`, text)
          }
          await py.runPythonAsync(`
import sys
sys.path.insert(0, '/')
          `)

          setPyodide(py)
          setLoading(false)
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to initialize Pyodide')
            setLoading(false)
          }
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
        // Set globals and call the API
        pyodide.globals.set('_csv_contents', pyodide.toPy(csvContents))
        pyodide.globals.set('_years', pyodide.toPy(years))
        pyodide.globals.set('_audit_csv', auditCsv)

        const result = await pyodide.runPythonAsync(`
import json
from nexo_tax.api import run
result = run(_csv_contents, _years, _audit_csv)
json.dumps(result)
        `)

        return JSON.parse(result)
      } catch (err) {
        throw new Error(`Calculation failed: ${err instanceof Error ? err.message : String(err)}`)
      }
    },
    [pyodide]
  )

  return { loading, error, pyodide, runCalculation }
}

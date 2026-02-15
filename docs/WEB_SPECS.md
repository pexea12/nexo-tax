# Specification: Web Interface

Browser-based frontend for the Nexo Tax Calculator. All computation runs locally via Pyodide (Python in WebAssembly) — no backend server required. User files never leave the browser.

## 1. Architecture

```
Browser
├── React 18 + TypeScript (UI)
├── Pyodide 0.24.0 (Python WebAssembly runtime)
└── nexo_tax Python package (same code as CLI)
```

- **Build**: Vite bundles the React app, then a post-build script copies the `nexo_tax/` Python package into `dist/nexo_tax/`.
- **Runtime**: Pyodide loads from CDN, mounts the Python package, and calls `nexo_tax.api.run()` directly.
- **Privacy**: CSV files are read as strings in the browser. No network requests are made during calculation.

## 2. User workflow

1. User opens the web page.
2. Pyodide loads in the background (loading indicator shown).
3. User uploads one or more Nexo CSV exports via drag-and-drop or file picker.
4. App parses the CSV to detect available tax years from the "Date / Time (UTC)" column.
5. User selects which years to calculate (checkboxes, all checked by default).
6. User optionally enables "Generate audit CSV files".
7. User clicks "Calculate Tax".
8. Console output (tax summary) is displayed in a scrollable monospace panel.
9. If audit CSVs were requested, download buttons appear for each generated file.

## 3. Components

### 3.1 FileUpload

- Drag-and-drop zone with click-to-browse fallback.
- Accepts multiple files; filters to `.csv` extension only.
- Visual feedback on drag-over (background color change).
- Disabled while Pyodide is loading or calculation is in progress.

### 3.2 YearSelector

- Auto-detects years from uploaded CSV date column using regex `/(\d{4})-/`.
- Renders a checkbox per detected year, all checked by default.
- Shows validation error if no years are selected.

### 3.3 ResultsView

- Scrollable `<pre>` element (max-height 600px) with monospace font.
- Displays the full console output from `nexo_tax.api.run()`.
- Shows "Calculating..." indicator while computation runs.

### 3.4 DownloadLinks

- One download button per generated audit CSV file.
- Creates Blob from CSV string content and triggers download via temporary `<a>` element.
- Cleans up Blob URL after download.

### 3.5 usePyodide hook

- Loads Pyodide from CDN (`https://cdn.jsdelivr.net/pyodide/v0.24.0/full/pyodide.js`).
- Initializes once on mount; adds `/nexo_tax` to `sys.path`.
- Exposes `runCalculation(csvContents: string[], years: number[], auditCsv: boolean)`.
- Converts JS arrays to Python via `.toPy()`, calls `nexo_tax.api.run()`, converts results back to JS.
- Returns `{ loading, error, pyodide, runCalculation }`.

## 4. Python API contract

The web interface calls `nexo_tax.api.run()`:

```python
def run(
    csv_contents: list[str],
    years: list[int],
    audit_csv: bool,
) -> dict[str, str | dict[str, str]]:
```

**Parameters:**
- `csv_contents`: CSV file contents as strings (not file paths).
- `years`: Tax years to calculate.
- `audit_csv`: Whether to generate detailed audit CSV files.

**Returns:**
```python
{
    "console": "...",          # All logged output (tax summaries)
    "audit_files": {           # Only present if audit_csv=True
        "acquisitions_2024.csv": "...",
        "interest_2024.csv": "...",
        "disposals_2024.csv": "...",
        "remaining_lots_2024.csv": "...",
        "card_analysis_2024.csv": "...",
    }
}
```

## 5. TypeScript types

```typescript
interface CalculationResult {
  console: string;
  audit_files: Record<string, string>;
}

interface DetectedYears {
  [year: number]: boolean;
}
```

## 6. Build process

```bash
npm run build
```

This runs:
1. `tsc` — TypeScript compilation.
2. `vite build` — Bundles React app into `dist/`.
3. `node scripts/copy-nexo-tax.js` — Copies `nexo_tax/` Python package into `dist/nexo_tax/`, skipping `__pycache__/` and `.pytest_cache/`.

Development server:
```bash
npm run dev    # Starts Vite dev server on localhost:5173
```

## 7. Makefile targets

```makefile
web:    # npm run build (produces dist/)
serve:  # npm run dev (starts localhost:5173)
```

## 8. Constraints and limitations

- Pyodide loads ~20 MB from CDN on first visit (cached by browser afterwards).
- Python package must be ES-module compatible (no CommonJS).
- CSV parsing functions in `api.py` accept string content (not file paths) for browser compatibility.
- The same Python codebase is used by both CLI and web — `api.py` is the shared entry point.
- No server-side state; each calculation is stateless and self-contained.

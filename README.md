# Nexo Tax Calculator

A Finnish crypto tax calculator for Nexo card cashback that computes capital income from NEXO rewards and capital gains/losses from disposals using FIFO (First In, First Out) cost basis.

## ⚠️ Disclaimer

**This tool is provided for informational purposes only.** Tax calculations are complex and jurisdiction-specific. While this tool aims to be accurate based on Finnish tax rules, **you are solely responsible for verifying all calculations and results**.

**Before filing your taxes:**
- Review the output carefully
- Consult with a Finnish tax professional (verotarkastaja) or tax advisor
- Verify your numbers in MyTax before submission
- Confirm FX rates and transaction classifications match your records

The authors and contributors accept **no liability** for incorrect tax calculations, missed deadlines, penalties, or any consequences arising from the use of this tool.

## Why This Tool?

Nexo recommends using Koinly for tax reporting, but Koinly has significant limitations:

- **Transaction limits**: Koinly's free tier caps at 10,000 transactions. Heavy Nexo card users can easily exceed this, forcing you into paid plans.
- **Cost**: Koinly plans start at ~€49/year and go up to €279/year for larger portfolios — just to file taxes on a credit card you already pay fees on.
- **Generic, not Nexo-specific**: Koinly is a general-purpose tool and does not understand Nexo's specific cashback mechanics or the Finnish Vero tax rules in detail.
- **No effective cashback rate**: Koinly tells you what you owe in tax, but does not tell you whether the Nexo card was actually worth using — i.e. the effective cashback rate after tax and FX spread costs.

This tool is **free, open-source, and built specifically for Finnish Nexo cardholders**. It runs entirely in your browser (no account, no upload, no subscription) and gives you the one number Koinly cannot: your true effective cashback rate.

## Overview

This tool helps Finnish tax residents calculate their tax liability on Nexo 2% card cashback rewards. It:

- Parses Nexo CSV export files
- Classifies transactions (cashback, interest, disposals, card purchases)
- Tracks NEXO acquisition costs using FIFO
- Calculates capital income from receiving cashback
- Computes capital gains/losses from NEXO disposals
- Analyzes card profitability (FX costs, cashback tax impact)
- Generates detailed audit trails for tax reporting

### Key Features

- **Multi-year support**: Process multiple tax years in one run
- **Comprehensive event classification**: Handles cashback, interest, exchanges, card purchases, repayments
- **FIFO lot tracking**: Properly tracks acquisition costs across years
- **FX conversion**: Uses observed FX rates from card transactions
- **Detailed reports**: ASCII summaries and optional CSV audit files
- **Card analysis**: Calculates effective cashback rate after tax and FX costs

## Development Setup

### Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup (Option 1: With Nix - Recommended)

Nix provides a reproducible development environment but is optional.

1. **Enter the development shell:**
   ```bash
   nix-shell
   ```
   This sets up Python 3.14 and uv package manager with all dependencies.

2. **Install/sync dependencies:**
   ```bash
   uv sync
   ```

3. **Run tests:**
   ```bash
   uv run pytest
   ```

4. **Check code style:**
   ```bash
   uv run ruff check .
   ```

5. **Auto-fix code style issues:**
   ```bash
   uv run ruff format . && uv run ruff check --fix .
   ```

### Setup (Option 2: Without Nix)

If you don't have Nix, you can install Python 3.14 and uv directly:

1. **Install Python 3.14** from [python.org](https://www.python.org) or your package manager
2. **Install uv:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **Install/sync dependencies:**
   ```bash
   uv sync
   ```

4. **Run tests:**
   ```bash
   uv run pytest
   ```

5. **Check code style:**
   ```bash
   uv run ruff check .
   ```

6. **Auto-fix code style issues:**
   ```bash
   uv run ruff format . && uv run ruff check --fix .
   ```

### Adding Dependencies

To add a new package to the project:

```bash
uv add package-name
```

For development-only dependencies (testing, linting, etc.):

```bash
uv add --group dev package-name
```

## Usage

### Arguments

- **`CSV_FILES`** (required): One or more Nexo CSV export files
- **`--year YEAR [YEAR ...]`** (required): One or more tax years to analyze (e.g., `--year 2024` or `--year 2023 2024`)
- **`--audit-csv`** (optional): Generate detailed CSV audit files for each year

### Examples

#### Quick Start with Sample Data

Try the tool with sample data to see how it works:

```bash
# Analyze the sample 2024 data
uv run nexo-tax data/sample_nexo_export.csv --year 2024

# Generate detailed audit CSV reports
uv run nexo-tax data/sample_nexo_export.csv --year 2024 --audit-csv
```

This will output a tax summary to the console and (with `--audit-csv`) create:
- `output/acquisitions_2024.csv` - All cashback/interest events
- `output/disposals_2024.csv` - All NEXO disposals with FIFO cost basis
- `output/remaining_lots_2024.csv` - Unsold NEXO still held
- `output/card_analysis_2024.csv` - Card purchase/repayment details

#### With Your Own Data

**Analyze a single year:**
```bash
uv run nexo-tax your_nexo_export.csv --year 2024
```

**Analyze multiple years:**
```bash
uv run nexo-tax your_nexo_export.csv --year 2023 2024 2025
```

**Generate detailed audit CSVs:**
```bash
uv run nexo-tax your_nexo_export.csv --year 2024 --audit-csv
```

**Process multiple CSV files:**
```bash
uv run nexo-tax export_2023.csv export_2024.csv --year 2023 2024
```

## Web Interface (No-Backend Browser Calculator)

A browser-based version lets you calculate taxes entirely in your browser with **zero data leaving your machine**.

### Why Use the Web Version?

- **Privacy**: Your CSV files never leave your browser — all calculations run locally via WebAssembly (Pyodide)
- **No setup**: No Python, no installation, no command line
- **Instant**: Load and calculate in seconds
- **Same results**: Uses the exact same Python code as the CLI

### Running the Dev Server

```bash
# Install Node.js dependencies (one-time setup)
cd web
npm install

# Start the dev server
npm run dev
```

Then open **http://localhost:5173** in your browser.

### Building for Production

```bash
# Build the static site
make web

# Output is in web/dist/ — ready to deploy to any static hosting
```

### How It Works

1. **Upload CSV files** by dragging and dropping or clicking to select
2. **Select tax years** (auto-detected from your data)
3. **Check "Generate audit CSV files"** if you want detailed reports
4. **Click "Calculate Tax"**
5. **View results** and download audit CSVs directly from the browser

The entire Nexo Tax Calculator Python code runs in WebAssembly (Pyodide), so your data is processed 100% locally.

## CSV Format

### Sample Data

For a quick trial without using your real transaction data, use the included sample:

```bash
uv run nexo-tax data/sample_nexo_export.csv --year 2024 --audit-csv
```

The sample file (`data/sample_nexo_export.csv`) contains realistic example transactions:
- **Cashback events**: 2% rewards on card purchases
- **Card purchases**: Nexo card transactions in USD/EUR
- **Repayments**: EUR → USD liquidations to clear card
- **Exchanges**: Selling/buying NEXO tokens
- **Interest**: NEXO interest earned

All names and amounts are anonymized for demonstration purposes.

### Getting Your Own Nexo CSV Exports

To analyze your real transactions, you need to export your transaction history from the Nexo website:

1. **Log in to your Nexo account** at https://app.nexo.io
2. Navigate to **Portfolio** → **Transactions** tab
3. **Select all transactions** by using the filter or date range selector to cover your entire transaction history
   - Use the date filter to select from the beginning of your first transaction
   - Or select "All" if available
4. **Export as CSV** by clicking the export button (usually a download or export icon)
5. **Save the CSV file** to your local machine
6. **Run the analyzer** on your exported file:
   ```bash
   uv run nexo-tax your_nexo_export.csv --year 2024
   ```

**Note:** The exported CSV file will contain all your transaction data including sensitive information. Keep it secure and do not share it publicly.

If you want to export multiple years separately, you can select different date ranges and export multiple files, then process them together:
```bash
uv run nexo-tax export_2023.csv export_2024.csv --year 2023 2024
```

### CSV Columns

The Nexo CSV export includes:
- **Type**: Transaction type (Cashback, Exchange, Nexo Card Purchase, etc.)
- **Transaction**: Unique transaction ID
- **Date / Time (UTC)**: Transaction timestamp
- **Input Currency**: Currency/asset sent
- **Input Amount**: Amount of input currency
- **Output Currency**: Currency/asset received (if applicable)
- **Output Amount**: Amount of output currency (if applicable)
- **USD Equivalent**: USD value at transaction time
- **Details**: Transaction description/merchant info

## Output

### Console Output

The tool prints a summary for each year including:

- **Cashback events**: Total NEXO received, EUR value, number of events
- **Interest events**: By asset, total amounts
- **Exchange buys**: By asset, total amounts
- **Disposals**: Total proceeds, cost basis, capital gains/losses
- **Card analysis**: Purchase amounts, repayments, FX spread, net benefit, effective rate

Example:
```
=== 2024 Annual Summary ===
Cashback: 50 events | 1,200.50 NEXO | 3,850.00 EUR
Card Purchases: 85 transactions | 45,000.00 EUR purchases | 48,500.00 USD
FX Spread Cost: 250.00 EUR
Cashback Tax (30%): 1,155.00 EUR
Net Card Benefit: 1,445.00 EUR (3.2% effective rate)
Capital Gains: 8,500.00 EUR (12 disposals)
```

### Audit CSV Files (with --audit-csv)

When using the `--audit-csv` flag, detailed reports are written to the `output/` directory:

- **`YEAR_cashback_audit.csv`**: All cashback events with EUR values and lot assignments
- **`YEAR_disposal_audit.csv`**: All NEXO disposals with cost basis and gain/loss calculations
- **`YEAR_card_analysis.csv`**: Card purchase and repayment details

## Tax Reporting

The numbers generated should be used for Finnish tax returns (MyTax):

1. **Capital income from cashback**: Enter total `total_cashback_eur` under "Other capital income"
2. **Capital gains/losses**: Enter `total_disposal_gain_eur` under "Capital gains – Crypto assets"
3. **Card cashback tax**: The 30% tax on cashback is automatically deducted in the analysis

See `docs/TAX_GUIDE.md` for more detailed tax information.

## Project Structure

```
nexo_tax/
├── cli/
│   └── main.py           # Entry point and CLI argument handling
├── parser.py             # CSV parsing and transaction classification
├── models.py             # Data classes for events and results
├── calculator.py         # Tax calculations and FIFO lot processing
├── fx.py                 # FX rate conversion utilities
└── report.py             # Report formatting and CSV output

docs/
├── SPECS.md              # Full specification and tax rules
├── TAX_GUIDE.md          # Finnish tax rules explanation
├── CARD_ANALYSIS_SPECS.md# Card profitability analysis details
└── INTEREST_SPECS.md     # Interest income handling

tests/
└── test_*.py             # Unit tests
```

## Important Notes

### Tax Classification

According to Finnish tax authority (Vero):
- Nexo 2% cashback is **taxable capital income** because it depends on prior crypto holdings (not just purchase volume)
- The acquisition cost of NEXO rewards is their EUR value at receipt date
- Later disposals trigger capital gains/losses using FIFO cost basis
- FX spreads on card transactions are not deductible (personal living costs)

### FIFO Cost Basis

The tool uses FIFO (First In, First Out) to match NEXO disposals against acquisition lots. Lots carry forward across years, so early disposals consume earlier acquisitions first.

### Currency Conversion

The tool derives USD/EUR exchange rates from your own card purchase transactions. If you have no card transactions in a year, external FX data may be needed.

## Contributing

### Code Style

- Type hints required on all functions
- Follow PEP 8
- All new code must include tests

### Running Tests

```bash
nix-shell --command "uv run pytest"
```

## License

MIT License - See [LICENSE](./LICENSE) file for details.

This software is provided "as-is" without warranty. See the [Disclaimer](#%EF%B8%8F-disclaimer) section above.

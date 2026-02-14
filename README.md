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
- Nix (for development environment)

### Quick Start

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
   nix-shell --command "uv run pytest"
   ```

4. **Check code style:**
   ```bash
   nix-shell --command "uv run ruff check ."
   ```

5. **Auto-fix code style issues:**
   ```bash
   nix-shell --command "uv run ruff format . && uv run ruff check --fix ."
   ```

### Adding Dependencies

To add a new package to the project:

```bash
nix-shell --command "uv add package-name"
```

For development-only dependencies (testing, linting, etc.):

```bash
nix-shell --command "uv add --group dev package-name"
```

## Usage

### Basic Command

```bash
nix-shell --command "uv run main.py EXPORT.csv --year 2024"
```

### Arguments

- **`CSV_FILES`** (required): One or more Nexo CSV export files
- **`--year YEAR [YEAR ...]`** (required): One or more tax years to analyze (e.g., `--year 2024` or `--year 2023 2024`)
- **`--audit-csv`** (optional): Generate detailed CSV audit files for each year

### Examples

**Analyze a single year:**
```bash
uv run main.py nexo_export.csv --year 2024
```

**Analyze multiple years:**
```bash
uv run main.py nexo_export.csv --year 2023 2024 2025
```

**Generate detailed audit CSVs:**
```bash
uv run main.py nexo_export.csv --year 2024 --audit-csv
```

**Process multiple CSV files:**
```bash
uv run main.py export_2023.csv export_2024.csv --year 2023 2024
```

## Getting Nexo CSV Exports

1. Log in to your Nexo account
2. Go to Portfolio → Transactions
3. Select the date range covering all your transactions
4. Export as CSV
5. Save the file(s) locally

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

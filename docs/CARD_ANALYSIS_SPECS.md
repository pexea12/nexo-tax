# Credit Card Cashback Profitability Analysis

## Motivation

The Nexo credit card earns 2% cashback in NEXO tokens on every purchase. However,
there is a hidden cost: Nexo converts EUR→USD at purchase time, and the user later
repays the credit line by converting EUR→USD again at repayment time. Exchange rate
differences (the "FX spread") mean the user often pays **more EUR** to repay than
the original purchase cost.

Additionally, the 2% cashback is taxable as capital income at 30% in Finland.

This analysis answers: **Is the 2% cashback actually profitable after accounting
for FX spread costs and the 30% tax?**

## Data Sources

Two transaction types from the Nexo CSV export:

### `Nexo Card Purchase` (USDX → EUR)

Each card purchase converts USD credit into EUR for the merchant. Tells us:
- **EUR amount** (Output Amount): what the merchant received
- **USD amount** (Input Amount): what was charged to the credit line

### `Exchange Liquidation` (EURX → USDX)

Each repayment converts EUR into USD to clear the credit line. Tells us:
- **EUR amount** (Input Amount): EUR spent to repay
- **USD amount** (Output Amount): USD credit cleared

## Calculation

Per year, aggregate:

| Metric | Formula |
|---|---|
| `total_purchase_eur` | Σ EUR from all `Nexo Card Purchase` |
| `total_purchase_usd` | Σ USD from all `Nexo Card Purchase` |
| `total_repayment_eur` | Σ EURX from all `Exchange Liquidation` |
| `total_repayment_usd` | Σ USDX from all `Exchange Liquidation` |
| `fx_spread_eur` | `total_repayment_eur` - `total_purchase_eur` (adjusted for USD mismatch) |
| `cashback_eur` | Net cashback from existing calculation (gross minus reversals) |
| `cashback_tax_eur` | `cashback_eur` × 0.30 |
| `net_benefit_eur` | `cashback_eur` - `cashback_tax_eur` - `fx_spread_eur` |
| `effective_rate_pct` | `net_benefit_eur` / `total_purchase_eur` × 100 |

### FX Spread Adjustment

Purchases and repayments may not balance within a year. To properly compute the FX
spread, we adjust for the USD mismatch:

```
purchase_rate = total_purchase_eur / total_purchase_usd
usd_mismatch = total_purchase_usd - total_repayment_usd
mismatch_eur = usd_mismatch * purchase_rate
fx_spread_eur = total_repayment_eur - (total_purchase_eur - mismatch_eur)
```

This gives the extra EUR paid purely due to the FX spread, excluding any difference
caused by repaying more or less USD than was spent.

## Worked Example

Suppose in 2025:
- Card purchases: 1000 EUR spent, 1100 USD charged (rate 0.909 EUR/USD)
- Repayments: 990 EUR spent, 1050 USD cleared (rate 0.943 EUR/USD)
- USD mismatch: 1100 - 1050 = 50 USD (still owed)
- Mismatch EUR: 50 × 0.909 = 45.45 EUR
- Adjusted purchase EUR: 1000 - 45.45 = 954.55 EUR (for the 1050 USD that was repaid)
- FX spread: 990 - 954.55 = 35.45 EUR
- Cashback: 20 EUR (net of reversals)
- Tax: 20 × 0.30 = 6.00 EUR
- Net benefit: 20 - 6 - 35.45 = -21.45 EUR (net loss)
- Effective rate: -21.45 / 1000 × 100 = -2.15%

In this example the FX spread wipes out the cashback benefit entirely.

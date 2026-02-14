# How the Program Calculates Your Tax

## Processing Pipeline

### Step 1 — Parse the Nexo CSV

The program reads your Nexo CSV export and classifies each row:

- **Cashback** (Input Currency = NEXO): every time you received 2% NEXO back on a card purchase. Creates acquisition lots for FIFO tracking.
- **Nexo Card Purchase** (Input Currency = xUSD/USDX, Output Currency = EUR): used to build a daily USD/EUR exchange rate table. Since Nexo reports everything in USD but Vero wants EUR, the program derives rates from your own card purchases (EUR amount / USD amount).
- **Exchange** (any crypto input or output): any swap involving crypto. If you sell crypto (e.g. NEXO → BTC), that's a taxable disposal. If you buy crypto (e.g. EURX → BTC), that creates an acquisition lot. A crypto-to-crypto swap (e.g. BTC → ETH) creates both a disposal and an acquisition.

### Step 2 — Convert USD to EUR

Each cashback event and disposal has a USD value from Nexo. The program converts these to EUR using the rate derived from your card purchases on the same date. If there's no card purchase on that exact date, it uses the nearest available date.

### Step 3 — FIFO lot tracking

Each acquisition event (cashback, interest, exchange buy) creates a "lot" — a record of (asset, date, quantity, EUR cost). Lots are tracked per asset in separate FIFO queues. When you dispose of a crypto asset (e.g. swap NEXO to BTC), the program consumes the oldest lots for that asset first (FIFO), computing the pro-rata cost basis from each lot.

## What to Report in MyTax (Vero)

### 1. Other Capital Income (Muut pääomatulot)

The total EUR value of all NEXO cashback received during the tax year.

Nexo's 2% cashback is taxable capital income at receipt because the cashback rate depends on your crypto holdings (minimum 5,000 EUR of crypto and 15% in NEXO). This matches Vero's "Case B" classification — income based on existing crypto assets.

### 2. Crypto Asset Disposals (Virtuaalivaluuttojen luovutukset)

For each disposal (selling, swapping, or spending NEXO), report:

- **Sale price (proceeds)**: EUR value at the time of disposal
- **Acquisition cost**: FIFO cost basis in EUR (sum of pro-rata costs from consumed lots)
- **Gain or loss**: proceeds minus acquisition cost

Any crypto-to-crypto swap (e.g. NEXO to BTC) counts as a disposal and is taxable. The received crypto (e.g. BTC) gets a new acquisition cost equal to the EUR proceeds of the swap.

### 3. Audit Trail

Run `make audit` to generate CSV files in `output/`:

- `acquisitions_YYYY.csv` — all cashback events with dates, amounts, and EUR values
- `disposals_YYYY.csv` — each disposal with FIFO lot breakdown and gain/loss
- `remaining_lots_YYYY.csv` — lots carrying forward to the next tax year

Keep these files in case Vero asks how you arrived at the numbers.

## Example Output (2025)

```
CASHBACK CAPITAL INCOME (Other capital income in MyTax)
  Cashback events:              870
  Total NEXO received:        1029.05412736
  Total value (EUR):                 983.46

CAPITAL GAINS/LOSSES (Capital gains - Crypto assets in MyTax)
  Disposal: Exchange NEXO Token to Bitcoin
    Date:            2025-11-11
    Quantity:              487.00000000 NEXO
    Proceeds (EUR):              440.75
    Cost basis:                  526.73
    Gain/Loss:                   -85.98

LOT QUEUE STATUS
  Remaining lots:               189
  Remaining BTC:            0.00488461
  Remaining NEXO:              542.05412736
```

In this example:
- Report **983.46 EUR** as other capital income
- Report the NEXO to BTC swap as a crypto disposal with a **-85.98 EUR** loss
- **542.05 NEXO** and **0.00488461 BTC** across 189 lots carry forward to 2026

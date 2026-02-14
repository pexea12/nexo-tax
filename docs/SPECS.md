# Project Specs

# Specification: Finnish Crypto Tax Calculator for Nexo Card Cashback

This document describes how Finnish tax rules (Vero) apply to Nexo card cashback and how a Python program should model and calculate the taxable amounts.

The user is a Finnish tax resident using the Nexo crypto card, receiving 2% cashback in NEXO tokens, with 5,000+ transactions per year.

## 1. Legal basis and scope

- Finland treats crypto and NEXO tokens as “crypto assets / virtual currencies” (virtuaalivaluutat).
- Taxable events relevant here:
  - Receiving cashback rewards in crypto when conditions depend on prior holdings.
  - Later disposal of those rewarded tokens (sell, swap, or spend).
- The program should cover two tax categories:
  - Capital income from **receiving** NEXO cashback (income at receipt).
  - Capital gains/losses from **disposing** NEXO rewards (gain/loss vs acquisition cost).

The program is for a private individual (not a business), and does not cover mining/staking/business income.

## 2. Nexo card mechanics (assumed)

User flow per transaction:

1. User makes a purchase in EUR (e.g. groceries 200 EUR).
2. Nexo card settles in USD (e.g. 205 USD), with its own FX spread.
3. Nexo credits 2% cashback in NEXO tokens, calculated from the USD amount (e.g. 4.1 USD worth of NEXO = 4 NEXO).
4. Later, user repays the card in EUR (e.g. 201 EUR) that is converted to USD inside Nexo.
5. User never needs to sell NEXO to pay the card; the repayment is purely fiat.

To get 2% cashback, the user must maintain at least 5,000 EUR of crypto and at least 15% in NEXO on Nexo. Therefore, the cashback is conditional on prior crypto holdings, not just spending volume.

## 3. Tax classification (Finnish rules)

### 3.1 Cashback: capital income (not tax-free rebate)

Vero’s “cashback rewards” guidance distinguishes:

- **Case A – Tax-free rebate**
  - Cashback percentage depends only on purchase volume.
  - Everyone using the card gets it, with no requirement to hold/lock crypto.
  - Treated like store bonuses or loyalty points → tax-free reduction of purchase price.

- **Case B – Taxable capital income based on crypto holdings**
  - Cashback percentage depends on how much crypto you hold (balance, tier, etc.).
  - You receive extra units of crypto without usage restriction.
  - Classified as capital income equal to the fair market value at receipt.

Nexo’s 2% requires minimum 5,000 EUR of crypto and 15% NEXO balance. This matches Case B: income **based on existing crypto assets**, so the reward is taxable capital income at receipt.

### 3.2 Later disposal: capital gains/losses

When the user later sells, swaps, or spends the NEXO rewards, this triggers a capital gain or loss event:

- Gain/loss = EUR value at disposal − EUR acquisition cost (using FIFO).
- Only disposal events are taxed as capital gains; holding is not taxable.

## 4. Core tax rules to implement

### 4.1 Acquisition cost of NEXO rewards

For each cashback event:

- Acquisition cost = **EUR value of the NEXO tokens at the moment of credit**.
- The same EUR amount is recognized as capital income in that tax year.

The program must convert the token value to EUR using a reliable rate at the credit timestamp (NEXO→USD→EUR or direct NEXO→EUR, depending on what data is available).

### 4.2 FX and card fees

- FX differences and spreads when paying **personal expenses** in foreign currency (e.g. groceries in EUR, card in USD) are **not deductible**. They are private living costs, even if the card is the only way to get cashback.
- These FX costs do **not** change the acquisition cost of NEXO rewards; they are not “expenses for acquiring crypto assets” but expenses for private consumption.
- Fees **directly attached to crypto disposals** (e.g. trading fee when selling NEXO) are allowed as transaction costs and can be included in the capital gain/loss calculation.

### 4.3 FIFO cost basis

- Finland applies FIFO for crypto: first acquired, first disposed.
- The program must:
  - Track each NEXO acquisition lot (date, quantity, total EUR cost).
  - Maintain a FIFO queue of lots.
  - When disposing NEXO (sell/swap/spend), match against oldest lots first to compute acquisition cost.

## 5. Data model for the Python program

Suggested internal representations:

```python
class CashbackEvent:
    date: datetime
    source_tx_id: str          # Link to original card transaction
    fiat_spent_eur: float      # e.g. 200.00
    fiat_settled_usd: float    # e.g. 205.00
    cashback_rate: float       # e.g. 0.02
    cashback_amount_nexo: float  # e.g. 4.0
    cashback_value_usd: float    # e.g. 4.1
    cashback_value_eur: float    # computed via FX, e.g. 3.80


class NexoLot:
    acquired_date: datetime
    quantity_nexo: float
    cost_eur_total: float       # equals cashback_value_eur for this lot
    remaining_nexo: float


class DisposalEvent:
    date: datetime
    quantity_nexo: float
    proceeds_eur: float        # sale/swap/spend value in EUR
    fee_eur: float             # disposal fee only
```

Program outputs:
- Annual total “Other capital income” from cashback = `sum of cashback_value_eur`.
- For each disposal: realized gain/loss using FIFO.
- Annual summary: total gains, total losses, net capital gains.

## 6. Algorithms

### 6.1 Processing raw transaction data

Input sources:
- CSV exports from Nexo: card payments, cashback credits, crypto trades, fees.
- External price/FX data if needed.

Steps:
- Read all card payment transactions.
- Identify cashback credits (NEXO inflows).
- For each cashback credit:
    - Link to the originating card payment (by timestamp and amount).
    - Extract cashback quantity and USD/quote value.
    - Convert to EUR using FX at the credit time.
    - Create CashbackEvent and corresponding NexoLot.
- Read all NEXO disposals (sells, swaps, card spending funded by NEXO):
  - For each, compute proceeds in EUR at disposal time.
  - Capture any explicit disposal fee.
  - Create DisposalEvent.

### 6.2 Calculating capital income from cashback

```python
def compute_cashback_income(cashback_events):
    total_income_eur = 0.0
    for ev in cashback_events:
        total_income_eur += ev.cashback_value_eur
    return total_income_eur
```

This total is what the user declares as “Other capital income” for the relevant year.

### 6.3 Maintaining FIFO lots for NEXO

```python
def add_nexo_lot(lots, event: CashbackEvent):
    lot = NexoLot(
        acquired_date = event.date,
        quantity_nexo = event.cashback_amount_nexo,
        cost_eur_total = event.cashback_value_eur,
        remaining_nexo = event.cashback_amount_nexo
    )
    lots.append(lot)
    lots.sort(key=lambda l: l.acquired_date)  # FIFO
```

### 6.4 Calculating capital gain/loss on disposal
```python
def dispose_nexo(lots, disposal: DisposalEvent):
    qty_to_dispose = disposal.quantity_nexo
    total_cost_eur = 0.0

    for lot in lots:
        if qty_to_dispose <= 0:
            break

        available = lot.remaining_nexo
        if available <= 0:
            continue

        used = min(available, qty_to_dispose)
        # Pro-rata cost from this lot
        cost_from_lot = lot.cost_eur_total * (used / lot.quantity_nexo)
        total_cost_eur += cost_from_lot

        lot.remaining_nexo -= used
        qty_to_dispose -= used

    if qty_to_dispose > 0:
        raise ValueError("Not enough NEXO to dispose")

    proceeds_after_fee = disposal.proceeds_eur - disposal.fee_eur
    gain_eur = proceeds_after_fee - total_cost_eur
    return gain_eur, total_cost_eur
```

The program then aggregates all gains and losses per year.

## 7. Worked examples

### 7.1 Single purchase, cashback, no disposal
Scenario:
- Purchase: 200 EUR groceries.
- Nexo settles: 205 USD.
- Cashback: 4.1 USD worth of NEXO = 4 NEXO.
- At that moment, 4.1 USD = 3.80 EUR.
- User repays card with 201 EUR (1 EUR FX cost).
- User never sells the 4 NEXO.

Tax logic:
- Cashback income: 3.80 EUR of capital income.
- Acquisition cost of 4 NEXO: 3.80 EUR total (0.95 EUR per NEXO).
- FX loss of 1 EUR on repayment is not deductible and not linked to NEXO acquisition cost.
- No capital gain/loss yet (no disposal).

Program behavior:
- One CashbackEvent with value 3.80 EUR.
- One NexoLot with 4 NEXO, cost 3.80 EUR.
- Annual output:
  - Cashback capital income: 3.80 EUR.
  - Capital gains: 0 EUR.

### 7.2 Later disposal of rewarded NEXO

Continuing the previous example:
- One year later, user sells 4 NEXO for 10 EUR, fee 0.20 EUR.

Tax logic:
- Proceeds: 10.00 EUR.
- Fee: 0.20 EUR.
- Net proceeds: 9.80 EUR.
- Acquisition cost: 3.80 EUR.
- Capital gain: 9.80 − 3.80 = 6.00 EUR.

Program behavior:
- FIFO uses the single lot (4 NEXO, cost 3.80 EUR).
- Gain of 6.00 EUR is recorded for that year.

### 7.3 Many cashback events, no disposal during the year

If the user receives many NEXO cashback lots but never disposes them in that year:
- All EUR values of cashback events are capital income for that year.
- No capital gains/losses are realized yet; NEXO lots carry forward to future years.

The program must support multi-year tracking of lots.

## 8. Reporting output for the user (MyTax)

The program should generate:
- Capital income from cashback
  - Per-year total EUR amount of NEXO cashback income.
  - Optional CSV with details: date, token amount, EUR value, source transaction.
- Capital gains/losses from NEXO disposals
  - For each disposal: date, quantity, proceeds, acquisition cost, gain/loss.
  - Annual totals: sum of gains, sum of losses, net gains.
- Audit trail
  - Detailed CSV per year listing:
    - All cashback events and corresponding lots.
    - All disposal events and which lots they consumed (FIFO mapping).

The user will manually enter these numbers into MyTax under:
- “Other capital income” → for total cashback EUR per year.
- “Capital income – Capital gains – Crypto assets” → for disposal gains/losses.

## 9. Assumptions and limitations

- Assumes Nexo exports provide enough data (timestamps, amounts, fiat values or rates).
- Assumes all Nexo 2% cashback is taxable because the rate depends on prior crypto/NEXO holdings.
- Uses actual cost basis and FIFO; does not implement optional “deemed acquisition cost” rules.
- User is responsible for verifying FX sources and the interpretation with Vero if needed.

# Finnish Crypto Tax Specification: Nexo Interest/Earn Products

This document explains how Finland's Tax Administration (Vero) treats **interest earned on cryptocurrency deposits** in Nexo (or similar platforms) for private individuals. Use this as a reference for extending your Python tax calculator.

## 1. Legal Basis and Classification

- **Crypto interest** from Nexo "Earn" or "Savings" products (on NEXO, USDC, BTC, etc.) is classified as **capital income** (pääomatulo), similar to bank interest.
- Vero treats this as income from **lending or locking crypto assets**.
- Taxable at the time each interest payment is **credited** to your account.

**Key Vero principle**: "Income is realised when virtual currency arrives into your account, into your wallet or is otherwise made available to you." [Vero guidance]

## 2. Nexo Interest Mechanics

**Typical daily flow**:
1. You deposit/hold crypto (e.g. 1 BTC, 1000 USDC, 5000 NEXO).
2. Nexo pays **daily interest** as additional crypto tokens (e.g. 0.0001 BTC, 1.2 USDC, 0.7 NEXO).
3. Interest rate depends on your holdings tier, lock period, etc.
4. Interest compounds (new interest can be earned on previous interest).

## 3. Tax Treatment

### 3.1 When Interest is Taxed: At Credit Time

**Each daily interest payment** triggers **capital income**:

    Interest Value EUR = Quantity received x EUR market price at credit timestamp

**Tax effect**:
- Add this EUR value to your **capital income** for that tax year
- This same EUR amount becomes the **acquisition cost** for FIFO tracking

### 3.2 Later Disposal: Capital Gains/Losses

When you sell/swap/spend the interest coins:

    Capital Gain/Loss = EUR value at disposal - EUR acquisition cost (from interest credit)

## 4. Data Model Extension for Python Program

Add these classes to your existing cashback spec:

```python
class InterestEvent:
    """Daily interest credit from Nexo Earn/Savings"""
    date: datetime              # Exact credit timestamp
    base_asset: str             # Asset earning interest (BTC, USDC, NEXO)
    interest_asset: str         # Asset received as interest (any crypto, not just NEXO)
    interest_quantity: float    # e.g. 0.0001 BTC, 1.2 USDC, 0.7 NEXO
    interest_value_usd: float   # Value shown by Nexo
    interest_value_eur: float   # EUR at credit time (required for tax)
```

**FIFO lots**: Interest in any crypto asset creates entries in the per-asset FIFO lot queue. For example, BTC interest creates BTC lots, NEXO interest creates NEXO lots. Each asset has its own FIFO queue for disposal tracking.

## 5. Tax Calculation Algorithm

### 5.1 Processing Interest Credits

Each daily interest payment:
1. Records capital income equal to the EUR value at credit time
2. Creates a FIFO lot for later disposal tracking (acquisition cost = same EUR value)

### 5.2 Annual Summary

Total "Other capital income" = cashback_income + interest_income

## 6. Worked Examples

### Example 1: Single Daily Interest Payment (No Disposal)

Scenario:
- Deposit: 1 BTC earning interest
- Daily interest: 0.0001 BTC credited on 2026-02-01
- BTC price at credit: 40,000 EUR
- Interest value: 0.0001 x 40,000 = 4.00 EUR

Tax 2026:
- Capital income: 4.00 EUR (reported as "Other capital income")
- Acquisition cost of 0.0001 BTC lot: 4.00 EUR
- Capital gains: 0 EUR (no disposal yet)

### Example 2: Interest + Later Sale

Continuing Example 1:
- Later sale: Sell 0.0001 BTC on 2026-12-01
- BTC price at sale: 50,000 EUR
- Proceeds: 0.0001 x 50,000 = 5.00 EUR
- Trading fee: 0.10 EUR

Tax 2026:
- Capital income (from interest): 4.00 EUR
- Capital gain: (5.00 - 0.10) - 4.00 = 0.90 EUR

### Example 3: Multiple Daily Payments (Compounding)

365 daily BTC interest payments:
- Day 1: 0.0001 BTC = 4.00 EUR income
- Day 2: 0.0001004 BTC = 4.02 EUR income (compounding)
- ...
- Day 365: Total interest income ~ 1,462.00 EUR

Tax requirement: Track 365 separate FIFO lots, each with its own acquisition cost based on daily EUR price.

## 7. Integration with Cashback Logic

**Unified FIFO queue**: Interest lots + cashback lots all use the same FIFO queue, sorted by acquired_date for FIFO matching on disposals.

**Annual reporting**:
- Total "Other capital income" = cashback_income + interest_income
- Capital gains/losses = from all disposals (FIFO across all lot types)

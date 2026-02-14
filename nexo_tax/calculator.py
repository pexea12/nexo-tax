from collections import deque
from decimal import Decimal

from nexo_tax.models import (
    AnnualSummary,
    CardAnalysisSummary,
    CardPurchaseEvent,
    CashbackEvent,
    CashbackReversalEvent,
    DisposalEvent,
    DisposalResult,
    ExchangeBuyEvent,
    InterestEvent,
    Lot,
    RepaymentEvent,
)


def build_lot_queue(
    cashback_events: list[CashbackEvent],
    interest_events: list[InterestEvent],
    exchange_buy_events: list[ExchangeBuyEvent],
) -> dict[str, deque[Lot]]:
    """Create per-asset FIFO lot queues from all acquisition sources, sorted by date."""
    lots_by_asset: dict[str, list[Lot]] = {}

    for ev in cashback_events:
        lots_by_asset.setdefault("NEXO", []).append(
            Lot(
                asset="NEXO",
                acquired_date=ev.date,
                quantity=ev.amount_nexo,
                cost_eur=ev.value_eur,
                remaining=ev.amount_nexo,
                tx_id=ev.tx_id,
                source="cashback",
            )
        )

    for ev in interest_events:
        lots_by_asset.setdefault(ev.asset, []).append(
            Lot(
                asset=ev.asset,
                acquired_date=ev.date,
                quantity=ev.amount,
                cost_eur=ev.value_eur,
                remaining=ev.amount,
                tx_id=ev.tx_id,
                source="interest",
            )
        )

    for ev in exchange_buy_events:
        lots_by_asset.setdefault(ev.asset, []).append(
            Lot(
                asset=ev.asset,
                acquired_date=ev.date,
                quantity=ev.amount,
                cost_eur=ev.value_eur,
                remaining=ev.amount,
                tx_id=ev.tx_id,
                source="exchange_buy",
            )
        )

    for asset_lots in lots_by_asset.values():
        asset_lots.sort(key=lambda lot: lot.acquired_date)

    return {asset: deque(lots) for asset, lots in lots_by_asset.items()}


def process_disposal(
    lots_by_asset: dict[str, deque[Lot]], disposal: DisposalEvent
) -> DisposalResult:
    """Process a single disposal against the per-asset FIFO lot queue.

    Consumes lots front-to-back, popping fully exhausted lots so each lot
    is visited at most once across all disposals.
    """
    lots = lots_by_asset.get(disposal.asset, deque())
    qty_needed = disposal.quantity
    total_cost = Decimal("0")
    lots_consumed: list[tuple[str, Decimal, Decimal]] = []

    while lots and qty_needed > 0:
        lot = lots[0]
        used = min(lot.remaining, qty_needed)
        cost_from_lot = lot.cost_eur * (used / lot.quantity)
        total_cost += cost_from_lot
        lot.remaining -= used
        qty_needed -= used
        lots_consumed.append((lot.tx_id, used, cost_from_lot))
        if lot.remaining <= 0:
            lots.popleft()

    if qty_needed > 0:
        raise ValueError(
            f"Not enough {disposal.asset} lots to cover disposal of "
            f"{disposal.quantity} {disposal.asset}. "
            f"Shortfall: {qty_needed} {disposal.asset}"
        )

    gain = disposal.proceeds_eur - disposal.fee_eur - total_cost

    return DisposalResult(
        disposal=disposal,
        cost_basis_eur=total_cost,
        gain_eur=gain,
        lots_consumed=lots_consumed,
    )


def compute_annual_summary(
    year: int,
    cashback_events: list[CashbackEvent],
    cashback_reversal_events: list[CashbackReversalEvent],
    interest_events: list[InterestEvent],
    exchange_buy_events: list[ExchangeBuyEvent],
    disposal_events: list[DisposalEvent],
    lots_by_asset: dict[str, deque[Lot]],
) -> AnnualSummary:
    """Compute annual tax summary for the given year."""
    year_cashback = [ev for ev in cashback_events if ev.date.year == year]
    year_reversals = [ev for ev in cashback_reversal_events if ev.date.year == year]
    year_interest = [ev for ev in interest_events if ev.date.year == year]
    year_exchange_buys = [ev for ev in exchange_buy_events if ev.date.year == year]
    year_disposals = [ev for ev in disposal_events if ev.date.year == year]

    total_cashback_nexo = sum(
        (ev.amount_nexo for ev in year_cashback), Decimal("0")
    )
    total_cashback_eur = sum(
        (ev.value_eur for ev in year_cashback), Decimal("0")
    )
    total_cashback_reversal_eur = sum(
        (ev.value_eur for ev in year_reversals), Decimal("0")
    )

    total_interest_by_asset: dict[str, Decimal] = {}
    for ev in year_interest:
        total_interest_by_asset[ev.asset] = (
            total_interest_by_asset.get(ev.asset, Decimal("0")) + ev.amount
        )
    total_interest_eur = sum(
        (ev.value_eur for ev in year_interest), Decimal("0")
    )

    total_exchange_buy_by_asset: dict[str, Decimal] = {}
    for ev in year_exchange_buys:
        total_exchange_buy_by_asset[ev.asset] = (
            total_exchange_buy_by_asset.get(ev.asset, Decimal("0")) + ev.amount
        )
    total_exchange_buy_eur = sum(
        (ev.value_eur for ev in year_exchange_buys), Decimal("0")
    )

    disposal_results = [process_disposal(lots_by_asset, d) for d in year_disposals]

    total_proceeds = sum(
        (r.disposal.proceeds_eur - r.disposal.fee_eur for r in disposal_results),
        Decimal("0"),
    )
    total_cost_basis = sum(
        (r.cost_basis_eur for r in disposal_results), Decimal("0")
    )
    total_gain = sum((r.gain_eur for r in disposal_results), Decimal("0"))

    remaining_by_asset: dict[str, Decimal] = {}
    remaining_lots = 0
    for asset, lots in lots_by_asset.items():
        for lot in lots:
            if lot.remaining > 0:
                remaining_lots += 1
                remaining_by_asset[asset] = (
                    remaining_by_asset.get(asset, Decimal("0")) + lot.remaining
                )

    return AnnualSummary(
        year=year,
        total_cashback_events=len(year_cashback),
        total_cashback_nexo=total_cashback_nexo,
        total_cashback_eur=total_cashback_eur,
        total_cashback_reversal_events=len(year_reversals),
        total_cashback_reversal_eur=total_cashback_reversal_eur,
        total_interest_events=len(year_interest),
        total_interest_by_asset=total_interest_by_asset,
        total_interest_eur=total_interest_eur,
        total_exchange_buy_events=len(year_exchange_buys),
        total_exchange_buy_by_asset=total_exchange_buy_by_asset,
        total_exchange_buy_eur=total_exchange_buy_eur,
        disposal_results=disposal_results,
        total_disposal_proceeds_eur=total_proceeds,
        total_disposal_cost_basis_eur=total_cost_basis,
        total_disposal_gain_eur=total_gain,
        remaining_lots=remaining_lots,
        remaining_by_asset=remaining_by_asset,
    )


_TAX_RATE = Decimal("0.30")


def compute_card_analysis(
    year: int,
    card_purchases: list[CardPurchaseEvent],
    repayments: list[RepaymentEvent],
    net_cashback_eur: Decimal,
) -> CardAnalysisSummary:
    """Compute credit card cashback profitability analysis for a year.

    Calculates FX spread cost, cashback tax, and effective cashback rate.
    """
    year_purchases = [ev for ev in card_purchases if ev.date.year == year]
    year_repayments = [ev for ev in repayments if ev.date.year == year]

    total_purchase_eur = sum(
        (ev.eur_amount for ev in year_purchases), Decimal("0")
    )
    total_purchase_usd = sum(
        (ev.usd_amount for ev in year_purchases), Decimal("0")
    )
    total_repayment_eur = sum(
        (ev.eur_amount for ev in year_repayments), Decimal("0")
    )
    total_repayment_usd = sum(
        (ev.usd_amount for ev in year_repayments), Decimal("0")
    )

    # FX spread: adjust for USD mismatch between purchases and repayments
    if total_purchase_usd > 0:
        purchase_rate = total_purchase_eur / total_purchase_usd
        usd_mismatch = total_purchase_usd - total_repayment_usd
        mismatch_eur = usd_mismatch * purchase_rate
        fx_spread_eur = total_repayment_eur - (total_purchase_eur - mismatch_eur)
    else:
        fx_spread_eur = Decimal("0")

    cashback_tax_eur = net_cashback_eur * _TAX_RATE
    net_benefit_eur = net_cashback_eur - cashback_tax_eur - fx_spread_eur

    if total_purchase_eur > 0:
        effective_rate_pct = net_benefit_eur / total_purchase_eur * 100
    else:
        effective_rate_pct = Decimal("0")

    return CardAnalysisSummary(
        year=year,
        total_purchase_eur=total_purchase_eur,
        total_purchase_usd=total_purchase_usd,
        total_repayment_eur=total_repayment_eur,
        total_repayment_usd=total_repayment_usd,
        fx_spread_eur=fx_spread_eur,
        cashback_eur=net_cashback_eur,
        cashback_tax_eur=cashback_tax_eur,
        net_benefit_eur=net_benefit_eur,
        effective_rate_pct=effective_rate_pct,
    )

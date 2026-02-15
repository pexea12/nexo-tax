import csv
import logging
from collections import deque
from pathlib import Path

from nexo_tax.models import (
    AnnualSummary,
    CardAnalysisSummary,
    CardPurchaseEvent,
    CashbackEvent,
    InterestEvent,
    Lot,
    RepaymentEvent,
)

logger = logging.getLogger(__name__)


def print_summary(summary: AnnualSummary) -> None:
    """Print a console tax summary for the year."""
    # Capital income: cashback (minus reversals) + interest
    net_cashback_eur = summary.total_cashback_eur - summary.total_cashback_reversal_eur
    total_income_eur = net_cashback_eur + summary.total_interest_eur

    lines = [
        f"\n{'=' * 60}",
        f"  Finnish Crypto Tax Summary — {summary.year}",
        f"{'=' * 60}",
        "",
        "  CAPITAL INCOME (Other capital income in MyTax)",
        f"  {'—' * 54}",
        "  Cashback:",
        f"    Events:              {summary.total_cashback_events:>10}",
        f"    NEXO received:       {summary.total_cashback_nexo:>18.8f}",
        f"    Value (EUR):         {summary.total_cashback_eur:>18.2f}",
    ]
    if summary.total_cashback_reversal_events > 0:
        lines += [
            "  Cashback reversals:",
            f"    Events:              {summary.total_cashback_reversal_events:>10}",
            f"    Reversed (EUR):      {summary.total_cashback_reversal_eur:>18.2f}",
            f"    Net cashback (EUR):  {net_cashback_eur:>18.2f}",
        ]
    lines += [
        "  Interest:",
        f"    Events:              {summary.total_interest_events:>10}",
    ]
    for asset, qty in sorted(summary.total_interest_by_asset.items()):
        lines.append(
            f"    {asset} received:{qty:>24.8f}"
        )
    lines += [
        f"    Value (EUR):         {summary.total_interest_eur:>18.2f}",
        f"  TOTAL CAPITAL INCOME:  {total_income_eur:>18.2f}",
    ]

    # Exchange buys (not income, just acquisitions)
    if summary.total_exchange_buy_events > 0:
        lines += [
            "",
            "  CRYPTO PURCHASES (not taxable, creates FIFO lots)",
            f"  {'—' * 54}",
            f"    Events:              {summary.total_exchange_buy_events:>10}",
        ]
        for asset, qty in sorted(summary.total_exchange_buy_by_asset.items()):
            lines.append(
                f"    {asset} acquired:{qty:>24.8f}"
            )
        lines.append(
            f"    Cost (EUR):          {summary.total_exchange_buy_eur:>18.2f}"
        )

    lines += [
        "",
        "  CAPITAL GAINS/LOSSES (Capital gains – Crypto assets in MyTax)",
        f"  {'—' * 54}",
    ]
    if summary.disposal_results:
        for result in summary.disposal_results:
            d = result.disposal
            acq_dates = [acq_date for _, _, _, acq_date in result.lots_consumed]
            earliest_acq = min(acq_dates).strftime("%Y-%m-%d")
            latest_acq = max(acq_dates).strftime("%Y-%m-%d")
            acq_str = earliest_acq if earliest_acq == latest_acq else f"{earliest_acq} — {latest_acq}"
            lines += [
                f"  Disposal: {d.description}",
                f"    Selling date:    {d.date.strftime('%Y-%m-%d')}",
                f"    Acquired:        {acq_str}",
                f"    Quantity:        {d.quantity:>18.8f} {d.asset}",
                f"    Proceeds (EUR):  {d.proceeds_eur:>18.2f}",
                f"    Fee (EUR):       {d.fee_eur:>18.2f}",
                f"    Cost basis:      {result.cost_basis_eur:>18.2f}",
                f"    Gain/Loss:       {result.gain_eur:>18.2f}",
                f"    Lots consumed:   {len(result.lots_consumed)}",
            ]
    else:
        lines.append("  No disposals during this year.")

    lines += [
        "",
        "  Disposal totals:",
        f"    Proceeds (EUR):  {summary.total_disposal_proceeds_eur:>18.2f}",
        f"    Cost basis:      {summary.total_disposal_cost_basis_eur:>18.2f}",
        f"    Net gain/loss:   {summary.total_disposal_gain_eur:>18.2f}",
        "",
        "  LOT QUEUE STATUS",
        f"  {'—' * 54}",
        f"  Remaining lots:        {summary.remaining_lots:>10}",
    ]
    for asset, qty in sorted(summary.remaining_by_asset.items()):
        lines.append(
            f"  Remaining {asset}:{qty:>24.8f}"
        )
    lines.append(f"\n{'=' * 60}\n")

    logger.info("\n".join(lines))


def write_audit_csv(
    output_dir: Path,
    year: int,
    cashback_events: list[CashbackEvent],
    interest_events: list[InterestEvent],
    lots_by_asset: dict[str, deque[Lot]],
    summary: AnnualSummary,
) -> None:
    """Write detailed audit CSV files for acquisitions and disposals."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Acquisitions CSV (cashback)
    acq_path = output_dir / f"acquisitions_{year}.csv"
    with open(acq_path, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(
            ["tx_id", "date", "amount_nexo", "value_usd", "value_eur", "merchant"]
        )
        for ev in cashback_events:
            if ev.date.year == year:
                writer.writerow(
                    [
                        ev.tx_id,
                        ev.date.strftime("%Y-%m-%d %H:%M:%S"),
                        f"{ev.amount_nexo:.8f}",
                        f"{ev.value_usd:.2f}",
                        f"{ev.value_eur:.2f}",
                        ev.merchant,
                    ]
                )
    logger.info("  Wrote %s", acq_path)

    # Interest CSV
    int_path = output_dir / f"interest_{year}.csv"
    with open(int_path, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(
            ["tx_id", "date", "asset", "amount", "value_usd", "value_eur", "source"]
        )
        for ev in interest_events:
            if ev.date.year == year:
                writer.writerow(
                    [
                        ev.tx_id,
                        ev.date.strftime("%Y-%m-%d %H:%M:%S"),
                        ev.asset,
                        f"{ev.amount:.8f}",
                        f"{ev.value_usd:.2f}",
                        f"{ev.value_eur:.2f}",
                        ev.source,
                    ]
                )
    logger.info("  Wrote %s", int_path)

    # Disposals CSV
    disp_path = output_dir / f"disposals_{year}.csv"
    with open(disp_path, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(
            [
                "tx_id",
                "date",
                "asset",
                "quantity",
                "proceeds_eur",
                "fee_eur",
                "cost_basis_eur",
                "gain_eur",
                "lots_consumed",
                "description",
            ]
        )
        for result in summary.disposal_results:
            d = result.disposal
            lots_detail = "; ".join(
                f"{tx_id}:{qty:.8f}@{cost:.2f}"
                for tx_id, qty, cost, _acq_date in result.lots_consumed
            )
            writer.writerow(
                [
                    d.tx_id,
                    d.date.strftime("%Y-%m-%d %H:%M:%S"),
                    d.asset,
                    f"{d.quantity:.8f}",
                    f"{d.proceeds_eur:.2f}",
                    f"{d.fee_eur:.2f}",
                    f"{result.cost_basis_eur:.2f}",
                    f"{result.gain_eur:.2f}",
                    lots_detail,
                    d.description,
                ]
            )
    logger.info("  Wrote %s", disp_path)

    # Remaining lots CSV
    lots_path = output_dir / f"remaining_lots_{year}.csv"
    with open(lots_path, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(
            [
                "tx_id",
                "asset",
                "acquired_date",
                "source",
                "original_qty",
                "remaining_qty",
                "cost_eur",
            ]
        )
        for asset in sorted(lots_by_asset):
            for lot in lots_by_asset[asset]:
                if lot.remaining > 0:
                    remaining_cost = lot.cost_eur * (lot.remaining / lot.quantity)
                    writer.writerow(
                        [
                            lot.tx_id,
                            lot.asset,
                            lot.acquired_date.strftime("%Y-%m-%d %H:%M:%S"),
                            lot.source,
                            f"{lot.quantity:.8f}",
                            f"{lot.remaining:.8f}",
                            f"{remaining_cost:.2f}",
                        ]
                    )
    logger.info("  Wrote %s", lots_path)


def print_card_analysis(analysis: CardAnalysisSummary) -> None:
    """Print credit card cashback profitability analysis."""
    lines = [
        f"\n{'=' * 60}",
        f"  Card Cashback Profitability — {analysis.year}",
        f"{'=' * 60}",
        "",
        "  CARD PURCHASES",
        f"  {'—' * 54}",
        f"    Total EUR spent:     {analysis.total_purchase_eur:>18.2f}",
        f"    Total USD charged:   {analysis.total_purchase_usd:>18.2f}",
        "",
        "  CREDIT LINE REPAYMENTS",
        f"  {'—' * 54}",
        f"    Total EUR spent:     {analysis.total_repayment_eur:>18.2f}",
        f"    Total USD cleared:   {analysis.total_repayment_usd:>18.2f}",
        "",
        "  PROFITABILITY",
        f"  {'—' * 54}",
        f"    FX spread cost:      {analysis.fx_spread_eur:>18.2f}",
        f"    Cashback earned:     {analysis.cashback_eur:>18.2f}",
        f"    Tax on cashback:     {analysis.cashback_tax_eur:>18.2f}",
        f"    Net benefit:         {analysis.net_benefit_eur:>18.2f}",
        f"    Effective rate:      {analysis.effective_rate_pct:>17.2f}%",
        f"\n{'=' * 60}\n",
    ]
    logger.info("\n".join(lines))


def write_card_analysis_csv(
    output_dir: Path,
    analysis: CardAnalysisSummary,
    card_purchases: list[CardPurchaseEvent],
    repayments: list[RepaymentEvent],
) -> None:
    """Write card analysis audit CSV with per-transaction detail."""
    output_dir.mkdir(parents=True, exist_ok=True)
    year = analysis.year

    path = output_dir / f"card_analysis_{year}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "section", "tx_id", "date", "eur_amount", "usd_amount", "merchant",
        ])

        for ev in card_purchases:
            if ev.date.year == year:
                writer.writerow([
                    "purchase",
                    ev.tx_id,
                    ev.date.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{ev.eur_amount:.2f}",
                    f"{ev.usd_amount:.2f}",
                    ev.merchant,
                ])

        for ev in repayments:
            if ev.date.year == year:
                writer.writerow([
                    "repayment",
                    ev.tx_id,
                    ev.date.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{ev.eur_amount:.2f}",
                    f"{ev.usd_amount:.2f}",
                    "",
                ])

        # Summary row
        writer.writerow([])
        writer.writerow(["metric", "value"])
        writer.writerow(["total_purchase_eur", f"{analysis.total_purchase_eur:.2f}"])
        writer.writerow(["total_purchase_usd", f"{analysis.total_purchase_usd:.2f}"])
        writer.writerow(["total_repayment_eur", f"{analysis.total_repayment_eur:.2f}"])
        writer.writerow(["total_repayment_usd", f"{analysis.total_repayment_usd:.2f}"])
        writer.writerow(["fx_spread_eur", f"{analysis.fx_spread_eur:.2f}"])
        writer.writerow(["cashback_eur", f"{analysis.cashback_eur:.2f}"])
        writer.writerow(["cashback_tax_eur", f"{analysis.cashback_tax_eur:.2f}"])
        writer.writerow(["net_benefit_eur", f"{analysis.net_benefit_eur:.2f}"])
        writer.writerow(["effective_rate_pct", f"{analysis.effective_rate_pct:.2f}"])

    logger.info("  Wrote %s", path)

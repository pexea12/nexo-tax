"""
API layer for tax calculations, callable from CLI and Pyodide.

This module provides a single entry point that takes CSV contents as strings
and returns console output and audit CSV files as strings.
"""

import csv
import io
import logging
from collections import deque
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from nexo_tax.calculator import (
    build_lot_queue,
    compute_annual_summary,
    compute_card_analysis,
)
from nexo_tax.fx import FxRateTable
from nexo_tax.models import (
    CardPurchaseEvent,
    CashbackEvent,
    CashbackReversalEvent,
    DisposalEvent,
    ExchangeBuyEvent,
    InterestEvent,
    RepaymentEvent,
)
from nexo_tax.report import (
    print_card_analysis,
    print_summary,
    write_audit_csv,
    write_card_analysis_csv,
)


def run(
    csv_contents: list[str], years: list[int], audit_csv: bool = False
) -> dict[str, str | dict[str, str]]:
    """
    Run tax calculation from CSV contents.

    Args:
        csv_contents: List of CSV file contents as strings
        years: List of tax years to report
        audit_csv: Whether to generate detailed audit CSV files

    Returns:
        dict with keys:
            - "console": str of all console output (print_summary, print_card_analysis)
            - "audit_files": dict mapping filename -> CSV content (if audit_csv=True)
    """
    # Capture logging output to string buffer
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("nexo_tax")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Parse all CSV contents
    result = parse_csvs_from_strings(csv_contents)
    logger.info("Parsed %d cashback events", len(result.cashback_events))
    logger.info(
        "Parsed %d cashback reversal events", len(result.cashback_reversal_events)
    )
    logger.info("Parsed %d interest events", len(result.interest_events))
    logger.info("Parsed %d exchange buy events", len(result.exchange_buy_events))
    logger.info(
        "Parsed %d FX observations (card purchases)",
        len(result.fx_observations),
    )
    logger.info("Parsed %d disposal events", len(result.disposal_events))
    logger.info("Parsed %d card purchase events", len(result.card_purchase_events))
    logger.info("Parsed %d repayment events", len(result.repayment_events))

    # Build FX rate table from all observations
    fx = FxRateTable(result.fx_observations)

    # Apply EUR values to all events
    for ev in result.cashback_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.cashback_reversal_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.interest_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.exchange_buy_events:
        ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

    for ev in result.disposal_events:
        ev.proceeds_eur = fx.convert_usd_to_eur(ev.proceeds_usd, ev.date)

    # Build per-asset FIFO lot queues from ALL acquisition sources (across years)
    lots_by_asset = build_lot_queue(
        result.cashback_events, result.interest_events, result.exchange_buy_events
    )

    audit_files: dict[str, str] = {}

    # Process each year sequentially (lots carry forward via FIFO)
    for year in sorted(years):
        summary = compute_annual_summary(
            year,
            result.cashback_events,
            result.cashback_reversal_events,
            result.interest_events,
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )
        print_summary(summary)

        # Card cashback profitability analysis
        net_cashback_eur = (
            summary.total_cashback_eur - summary.total_cashback_reversal_eur
        )
        card_analysis = compute_card_analysis(
            year,
            result.card_purchase_events,
            result.repayment_events,
            net_cashback_eur,
        )
        print_card_analysis(card_analysis)

        if audit_csv:
            # Generate audit CSV files as strings
            audit_files.update(
                _generate_audit_csvs(
                    year,
                    result.cashback_events,
                    result.interest_events,
                    lots_by_asset,
                    summary,
                    result.card_purchase_events,
                    result.repayment_events,
                    card_analysis,
                )
            )

    return {
        "console": log_buffer.getvalue(),
        "audit_files": audit_files,
    }


def _generate_audit_csvs(
    year: int,
    cashback_events: list[CashbackEvent],
    interest_events: list[InterestEvent],
    lots_by_asset: dict[str, deque],
    summary,
    card_purchase_events: list[CardPurchaseEvent],
    repayment_events: list[RepaymentEvent],
    card_analysis,
) -> dict[str, str]:
    """Generate audit CSV files as strings (in-memory)."""
    files = {}

    # Acquisitions CSV (cashback)
    acq_buffer = io.StringIO()
    writer = csv.writer(acq_buffer, quoting=csv.QUOTE_ALL)
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
    files[f"acquisitions_{year}.csv"] = acq_buffer.getvalue()

    # Interest CSV
    int_buffer = io.StringIO()
    writer = csv.writer(int_buffer, quoting=csv.QUOTE_ALL)
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
    files[f"interest_{year}.csv"] = int_buffer.getvalue()

    # Disposals CSV
    disp_buffer = io.StringIO()
    writer = csv.writer(disp_buffer, quoting=csv.QUOTE_ALL)
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
            for tx_id, qty, cost in result.lots_consumed
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
    files[f"disposals_{year}.csv"] = disp_buffer.getvalue()

    # Remaining lots CSV
    lots_buffer = io.StringIO()
    writer = csv.writer(lots_buffer, quoting=csv.QUOTE_ALL)
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
    files[f"remaining_lots_{year}.csv"] = lots_buffer.getvalue()

    # Card analysis CSV
    card_buffer = io.StringIO()
    writer = csv.writer(card_buffer, quoting=csv.QUOTE_ALL)
    writer.writerow([
        "section", "tx_id", "date", "eur_amount", "usd_amount", "merchant",
    ])

    for ev in card_purchase_events:
        if ev.date.year == year:
            writer.writerow([
                "purchase",
                ev.tx_id,
                ev.date.strftime("%Y-%m-%d %H:%M:%S"),
                f"{ev.eur_amount:.2f}",
                f"{ev.usd_amount:.2f}",
                ev.merchant,
            ])

    for ev in repayment_events:
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
    writer.writerow(["total_purchase_eur", f"{card_analysis.total_purchase_eur:.2f}"])
    writer.writerow(["total_purchase_usd", f"{card_analysis.total_purchase_usd:.2f}"])
    writer.writerow(["total_repayment_eur", f"{card_analysis.total_repayment_eur:.2f}"])
    writer.writerow(["total_repayment_usd", f"{card_analysis.total_repayment_usd:.2f}"])
    writer.writerow(["fx_spread_eur", f"{card_analysis.fx_spread_eur:.2f}"])
    writer.writerow(["cashback_eur", f"{card_analysis.cashback_eur:.2f}"])
    writer.writerow(["cashback_tax_eur", f"{card_analysis.cashback_tax_eur:.2f}"])
    writer.writerow(["net_benefit_eur", f"{card_analysis.net_benefit_eur:.2f}"])
    writer.writerow(["effective_rate_pct", f"{card_analysis.effective_rate_pct:.2f}"])

    files[f"card_analysis_{year}.csv"] = card_buffer.getvalue()

    return files


# --- Parser functions adapted to work with string contents ---

_INTEREST_TYPES = {"Interest", "Fixed Term Interest", "Exchange Cashback"}
_USD_CURRENCIES = {"USD", "xUSD", "USDX"}
_FIAT_CURRENCIES = {"EUR", "EURX", "USD", "xUSD", "USDX"}


def _is_crypto(currency: str) -> bool:
    """Return True if the currency is a crypto asset (not fiat)."""
    return currency not in _FIAT_CURRENCIES


def _parse_usd(val: str) -> Decimal:
    """Strip '$' prefix and return Decimal."""
    return Decimal(val.lstrip("$"))


def _extract_merchant(details: str) -> str:
    """Extract merchant name from Details field, stripping 'approved / ' prefix."""
    prefix = "approved / "
    if details.startswith(prefix):
        return details[len(prefix) :]
    return details


def parse_csvs_from_strings(csv_contents: list[str]):
    """Parse multiple CSV contents and return merged ParseResult."""
    from nexo_tax.parser import ParseResult

    merged = ParseResult(
        cashback_events=[],
        cashback_reversal_events=[],
        interest_events=[],
        exchange_buy_events=[],
        fx_observations=[],
        disposal_events=[],
        card_purchase_events=[],
        repayment_events=[],
    )

    for content in csv_contents:
        result = parse_csv_from_string(content)
        merged.cashback_events.extend(result.cashback_events)
        merged.cashback_reversal_events.extend(result.cashback_reversal_events)
        merged.interest_events.extend(result.interest_events)
        merged.exchange_buy_events.extend(result.exchange_buy_events)
        merged.fx_observations.extend(result.fx_observations)
        merged.disposal_events.extend(result.disposal_events)
        merged.card_purchase_events.extend(result.card_purchase_events)
        merged.repayment_events.extend(result.repayment_events)

    merged.cashback_events.sort(key=lambda event: event.date)
    merged.cashback_reversal_events.sort(key=lambda event: event.date)
    merged.interest_events.sort(key=lambda event: event.date)
    merged.exchange_buy_events.sort(key=lambda event: event.date)
    merged.fx_observations.sort(key=lambda observation: observation.date)
    merged.disposal_events.sort(key=lambda event: event.date)
    merged.card_purchase_events.sort(key=lambda event: event.date)
    merged.repayment_events.sort(key=lambda event: event.date)

    return merged


def parse_csv_from_string(content: str):
    """Parse Nexo CSV export from string content and classify transactions."""
    from nexo_tax.parser import FxObservation, ParseResult

    cashback_events: list[CashbackEvent] = []
    cashback_reversal_events: list[CashbackReversalEvent] = []
    interest_events: list[InterestEvent] = []
    exchange_buy_events: list[ExchangeBuyEvent] = []
    fx_observations: list[FxObservation] = []
    disposal_events: list[DisposalEvent] = []
    card_purchase_events: list[CardPurchaseEvent] = []
    repayment_events: list[RepaymentEvent] = []

    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        tx_type = row["Type"]
        tx_id = row["Transaction"]
        date = datetime.strptime(row["Date / Time (UTC)"], "%Y-%m-%d %H:%M:%S")
        input_currency = row["Input Currency"]
        input_amount = Decimal(row["Input Amount"])
        output_currency = row["Output Currency"]
        value_usd = _parse_usd(row["USD Equivalent"])
        merchant = _extract_merchant(row["Details"])

        if tx_type == "Cashback" and input_currency == "NEXO":
            cashback_events.append(
                CashbackEvent(
                    tx_id=tx_id,
                    date=date,
                    amount_nexo=input_amount,
                    value_usd=value_usd,
                    value_eur=Decimal("0"),
                    merchant=merchant,
                )
            )
        elif (
            tx_type in _INTEREST_TYPES
            and input_amount > 0
            and _is_crypto(input_currency)
        ):
            interest_events.append(
                InterestEvent(
                    tx_id=tx_id,
                    date=date,
                    asset=input_currency,
                    amount=input_amount,
                    value_usd=value_usd,
                    value_eur=Decimal("0"),
                    source=tx_type,
                )
            )
        elif tx_type == "Nexo Card Cashback Reversal":
            cashback_reversal_events.append(
                CashbackReversalEvent(
                    tx_id=tx_id,
                    date=date,
                    value_usd=value_usd,
                    value_eur=Decimal("0"),
                )
            )
        elif tx_type in {"Exchange", "Exchange Collateral"}:
            # Selling crypto → disposal
            if _is_crypto(input_currency):
                disposal_events.append(
                    DisposalEvent(
                        tx_id=tx_id,
                        date=date,
                        asset=input_currency,
                        quantity=abs(input_amount),
                        proceeds_usd=value_usd,
                        proceeds_eur=Decimal("0"),
                        fee_eur=Decimal("0"),
                        description=merchant,
                    )
                )
            # Buying crypto → exchange buy
            if _is_crypto(output_currency):
                output_amount = Decimal(row["Output Amount"])
                exchange_buy_events.append(
                    ExchangeBuyEvent(
                        tx_id=tx_id,
                        date=date,
                        asset=output_currency,
                        amount=output_amount,
                        spent_amount=abs(input_amount),
                        spent_currency=input_currency,
                        value_usd=value_usd,
                        value_eur=Decimal("0"),
                    )
                )
        elif (
            tx_type in {"Manual Sell Order", "Withdrawal"}
            and _is_crypto(input_currency)
        ):
            disposal_events.append(
                DisposalEvent(
                    tx_id=tx_id,
                    date=date,
                    asset=input_currency,
                    quantity=abs(input_amount),
                    proceeds_usd=value_usd,
                    proceeds_eur=Decimal("0"),
                    fee_eur=Decimal("0"),
                    description=merchant,
                )
            )
        elif tx_type == "Top up Crypto" and _is_crypto(input_currency):
            exchange_buy_events.append(
                ExchangeBuyEvent(
                    tx_id=tx_id,
                    date=date,
                    asset=input_currency,
                    amount=input_amount,
                    spent_amount=input_amount,
                    spent_currency=input_currency,
                    value_usd=value_usd,
                    value_eur=Decimal("0"),
                )
            )
        elif (
            tx_type == "Nexo Card Purchase"
            and input_currency in _USD_CURRENCIES
            and output_currency == "EUR"
        ):
            usd_amount = abs(input_amount)
            eur_amount = Decimal(row["Output Amount"])
            fx_observations.append(
                FxObservation(
                    date=date, eur_amount=eur_amount, usd_amount=usd_amount
                )
            )
            card_purchase_events.append(
                CardPurchaseEvent(
                    tx_id=tx_id,
                    date=date,
                    eur_amount=eur_amount,
                    usd_amount=usd_amount,
                    merchant=merchant,
                )
            )
        elif (
            tx_type == "Exchange Liquidation"
            and input_currency in {"EUR", "EURX"}
            and output_currency in _USD_CURRENCIES
        ):
            repayment_events.append(
                RepaymentEvent(
                    tx_id=tx_id,
                    date=date,
                    eur_amount=abs(input_amount),
                    usd_amount=Decimal(row["Output Amount"]),
                )
            )

    # Sort all by date ascending (CSV is reverse chronological)
    cashback_events.sort(key=lambda event: event.date)
    cashback_reversal_events.sort(key=lambda event: event.date)
    interest_events.sort(key=lambda event: event.date)
    exchange_buy_events.sort(key=lambda event: event.date)
    fx_observations.sort(key=lambda observation: observation.date)
    disposal_events.sort(key=lambda event: event.date)
    card_purchase_events.sort(key=lambda event: event.date)
    repayment_events.sort(key=lambda event: event.date)

    return ParseResult(
        cashback_events=cashback_events,
        cashback_reversal_events=cashback_reversal_events,
        interest_events=interest_events,
        exchange_buy_events=exchange_buy_events,
        fx_observations=fx_observations,
        disposal_events=disposal_events,
        card_purchase_events=card_purchase_events,
        repayment_events=repayment_events,
    )

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from nexo_tax.models import (
    CardPurchaseEvent,
    CashbackEvent,
    CashbackReversalEvent,
    DisposalEvent,
    ExchangeBuyEvent,
    InterestEvent,
    RepaymentEvent,
)


@dataclass
class FxObservation:
    date: datetime
    eur_amount: Decimal
    usd_amount: Decimal


@dataclass
class ParseResult:
    cashback_events: list[CashbackEvent]
    cashback_reversal_events: list[CashbackReversalEvent]
    interest_events: list[InterestEvent]
    exchange_buy_events: list[ExchangeBuyEvent]
    fx_observations: list[FxObservation]
    disposal_events: list[DisposalEvent]
    card_purchase_events: list[CardPurchaseEvent]
    repayment_events: list[RepaymentEvent]


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


def parse_csvs(paths: list[Path]) -> ParseResult:
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

    for path in paths:
        result = parse_csv(path)
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


def parse_csv(path: Path) -> ParseResult:
    """Parse Nexo CSV export and classify transactions."""
    cashback_events: list[CashbackEvent] = []
    cashback_reversal_events: list[CashbackReversalEvent] = []
    interest_events: list[InterestEvent] = []
    exchange_buy_events: list[ExchangeBuyEvent] = []
    fx_observations: list[FxObservation] = []
    disposal_events: list[DisposalEvent] = []
    card_purchase_events: list[CardPurchaseEvent] = []
    repayment_events: list[RepaymentEvent] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
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

from collections import deque
from datetime import datetime
from decimal import Decimal

import pytest

from nexo_tax.calculator import (
    build_lot_queue,
    compute_annual_summary,
    process_disposal,
)
from nexo_tax.models import (
    CashbackEvent,
    CashbackReversalEvent,
    DisposalEvent,
    ExchangeBuyEvent,
    InterestEvent,
    Lot,
)


def _cashback(tx_id: str, date_str: str, amount: str, eur: str) -> CashbackEvent:
    return CashbackEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        amount_nexo=Decimal(amount),
        value_usd=Decimal("0"),
        value_eur=Decimal(eur),
        merchant="Test",
    )


def _interest(
    tx_id: str, date_str: str, amount: str, eur: str, asset: str = "NEXO"
) -> InterestEvent:
    return InterestEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        asset=asset,
        amount=Decimal(amount),
        value_usd=Decimal("0"),
        value_eur=Decimal(eur),
        source="Interest",
    )


def _exchange_buy(
    tx_id: str, date_str: str, amount: str, eur: str, asset: str = "NEXO"
) -> ExchangeBuyEvent:
    return ExchangeBuyEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        asset=asset,
        amount=Decimal(amount),
        spent_amount=Decimal("0"),
        spent_currency="EURX",
        value_usd=Decimal("0"),
        value_eur=Decimal(eur),
    )


def _disposal(
    tx_id: str, date_str: str, qty: str, proceeds_eur: str, asset: str = "NEXO"
) -> DisposalEvent:
    return DisposalEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        asset=asset,
        quantity=Decimal(qty),
        proceeds_usd=Decimal("0"),
        proceeds_eur=Decimal(proceeds_eur),
        fee_eur=Decimal("0"),
        description="Test disposal",
    )


class TestBuildLotQueue:
    def test_creates_lots_sorted_by_date(self) -> None:
        cashbacks = [
            _cashback("TX2", "2025-06-15", "10", "8.50"),
            _cashback("TX1", "2025-01-10", "5", "4.00"),
        ]
        lots_by_asset = build_lot_queue(cashbacks, [], [])
        lots = lots_by_asset["NEXO"]
        assert len(lots) == 2
        assert lots[0].tx_id == "TX1"
        assert lots[1].tx_id == "TX2"
        assert lots[0].remaining == Decimal("5")

    def test_creates_separate_per_asset_queues(self) -> None:
        nexo_interest = [_interest("INT1", "2025-01-01", "2", "1.50")]
        btc_interest = [_interest("INT2", "2025-02-01", "0.001", "40.00", asset="BTC")]
        lots_by_asset = build_lot_queue([], nexo_interest + btc_interest, [])
        assert len(lots_by_asset["NEXO"]) == 1
        assert lots_by_asset["NEXO"][0].tx_id == "INT1"
        assert lots_by_asset["NEXO"][0].source == "interest"
        assert len(lots_by_asset["BTC"]) == 1
        assert lots_by_asset["BTC"][0].tx_id == "INT2"
        assert lots_by_asset["BTC"][0].asset == "BTC"

    def test_mixed_sources_sorted_by_date(self) -> None:
        cashbacks = [_cashback("CB1", "2025-03-01", "5", "4.00")]
        interests = [_interest("INT1", "2025-01-01", "2", "1.50")]
        buys = [_exchange_buy("BUY1", "2025-02-01", "100", "90.00")]
        lots_by_asset = build_lot_queue(cashbacks, interests, buys)
        lots = lots_by_asset["NEXO"]
        assert len(lots) == 3
        assert lots[0].tx_id == "INT1"
        assert lots[0].source == "interest"
        assert lots[1].tx_id == "BUY1"
        assert lots[1].source == "exchange_buy"
        assert lots[2].tx_id == "CB1"
        assert lots[2].source == "cashback"


class TestProcessDisposal:
    def test_single_lot_full_consumption(self) -> None:
        lot = Lot(
            asset="NEXO",
            acquired_date=datetime(2025, 1, 1),
            quantity=Decimal("10"),
            cost_eur=Decimal("8"),
            remaining=Decimal("10"),
            tx_id="LOT1",
        )
        lots = deque([lot])
        disposal = _disposal("D1", "2025-06-01", "10", "15")
        result = process_disposal({"NEXO": lots}, disposal)
        assert result.cost_basis_eur == Decimal("8")
        assert result.gain_eur == Decimal("7")  # 15 - 8
        assert lot.remaining == Decimal("0")
        assert len(lots) == 0

    def test_partial_lot_consumption(self) -> None:
        lots = deque([
            Lot(
                asset="NEXO",
                acquired_date=datetime(2025, 1, 1),
                quantity=Decimal("10"),
                cost_eur=Decimal("8"),
                remaining=Decimal("10"),
                tx_id="LOT1",
            )
        ])
        disposal = _disposal("D1", "2025-06-01", "4", "6")
        result = process_disposal({"NEXO": lots}, disposal)
        assert result.cost_basis_eur == Decimal("3.2")
        assert result.gain_eur == Decimal("2.8")
        assert lots[0].remaining == Decimal("6")

    def test_fifo_across_multiple_lots(self) -> None:
        lot1 = Lot(
            asset="NEXO",
            acquired_date=datetime(2025, 1, 1),
            quantity=Decimal("5"),
            cost_eur=Decimal("4"),
            remaining=Decimal("5"),
            tx_id="LOT1",
        )
        lot2 = Lot(
            asset="NEXO",
            acquired_date=datetime(2025, 2, 1),
            quantity=Decimal("10"),
            cost_eur=Decimal("9"),
            remaining=Decimal("10"),
            tx_id="LOT2",
        )
        lots = deque([lot1, lot2])
        disposal = _disposal("D1", "2025-06-01", "8", "20")
        result = process_disposal({"NEXO": lots}, disposal)
        assert result.cost_basis_eur == Decimal("6.7")
        assert result.gain_eur == Decimal("13.3")
        assert lot1.remaining == Decimal("0")
        assert lot2.remaining == Decimal("7")
        assert len(result.lots_consumed) == 2

    def test_insufficient_lots_raises(self) -> None:
        lots = deque([
            Lot(
                asset="NEXO",
                acquired_date=datetime(2025, 1, 1),
                quantity=Decimal("5"),
                cost_eur=Decimal("4"),
                remaining=Decimal("5"),
                tx_id="LOT1",
            )
        ])
        disposal = _disposal("D1", "2025-06-01", "10", "20")
        with pytest.raises(ValueError, match="Not enough NEXO"):
            process_disposal({"NEXO": lots}, disposal)

    def test_disposal_with_fee(self) -> None:
        lots = deque([
            Lot(
                asset="NEXO",
                acquired_date=datetime(2025, 1, 1),
                quantity=Decimal("10"),
                cost_eur=Decimal("8"),
                remaining=Decimal("10"),
                tx_id="LOT1",
            )
        ])
        disposal = DisposalEvent(
            tx_id="D1",
            date=datetime(2025, 6, 1),
            asset="NEXO",
            quantity=Decimal("10"),
            proceeds_usd=Decimal("0"),
            proceeds_eur=Decimal("15"),
            fee_eur=Decimal("0.50"),
            description="Test",
        )
        result = process_disposal({"NEXO": lots}, disposal)
        assert result.gain_eur == Decimal("6.50")

    def test_disposal_from_btc_queue(self) -> None:
        btc_lots = deque([
            Lot(
                asset="BTC",
                acquired_date=datetime(2025, 1, 1),
                quantity=Decimal("0.01"),
                cost_eur=Decimal("400"),
                remaining=Decimal("0.01"),
                tx_id="LOT_BTC",
            )
        ])
        disposal = _disposal("D1", "2025-06-01", "0.005", "300", asset="BTC")
        result = process_disposal({"BTC": btc_lots}, disposal)
        assert result.cost_basis_eur == Decimal("200")
        assert result.gain_eur == Decimal("100")
        assert btc_lots[0].remaining == Decimal("0.005")

    def test_disposal_wrong_asset_raises(self) -> None:
        nexo_lots = deque([
            Lot(
                asset="NEXO",
                acquired_date=datetime(2025, 1, 1),
                quantity=Decimal("100"),
                cost_eur=Decimal("80"),
                remaining=Decimal("100"),
                tx_id="LOT1",
            )
        ])
        btc_disposal = _disposal("D1", "2025-06-01", "0.01", "500", asset="BTC")
        with pytest.raises(ValueError, match="Not enough BTC"):
            process_disposal({"NEXO": nexo_lots}, btc_disposal)


class TestComputeAnnualSummary:
    def test_summary_with_all_sources(self) -> None:
        cashbacks = [
            _cashback("TX1", "2025-01-10", "5", "4.00"),
            _cashback("TX2", "2025-06-15", "10", "8.50"),
        ]
        interests = [_interest("INT1", "2025-02-01", "1", "0.80")]
        buys = [_exchange_buy("BUY1", "2025-01-05", "100", "90.00")]
        disposals = [_disposal("D1", "2025-08-01", "8", "20")]
        lots_by_asset = build_lot_queue(cashbacks, interests, buys)
        summary = compute_annual_summary(
            2025, cashbacks, [], interests, buys, disposals, lots_by_asset
        )

        assert summary.total_cashback_events == 2
        assert summary.total_cashback_nexo == Decimal("15")
        assert summary.total_cashback_eur == Decimal("12.50")
        assert summary.total_cashback_reversal_events == 0
        assert summary.total_cashback_reversal_eur == Decimal("0")
        assert summary.total_interest_events == 1
        assert summary.total_interest_by_asset == {"NEXO": Decimal("1")}
        assert summary.total_interest_eur == Decimal("0.80")
        assert summary.total_exchange_buy_events == 1
        assert summary.total_exchange_buy_by_asset == {"NEXO": Decimal("100")}
        assert len(summary.disposal_results) == 1

    def test_summary_with_cashback_reversals(self) -> None:
        cashbacks = [_cashback("TX1", "2025-01-10", "5", "4.00")]
        reversals = [
            CashbackReversalEvent(
                tx_id="REV1",
                date=datetime.strptime("2025-03-01", "%Y-%m-%d"),
                value_usd=Decimal("0"),
                value_eur=Decimal("1.50"),
            )
        ]
        lots_by_asset = build_lot_queue(cashbacks, [], [])
        summary = compute_annual_summary(
            2025, cashbacks, reversals, [], [], [], lots_by_asset
        )
        assert summary.total_cashback_eur == Decimal("4.00")
        assert summary.total_cashback_reversal_events == 1
        assert summary.total_cashback_reversal_eur == Decimal("1.50")

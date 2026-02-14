from datetime import datetime
from decimal import Decimal

from nexo_tax.calculator import compute_card_analysis
from nexo_tax.models import CardPurchaseEvent, RepaymentEvent


def _purchase(
    tx_id: str, date_str: str, eur: str, usd: str
) -> CardPurchaseEvent:
    return CardPurchaseEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        eur_amount=Decimal(eur),
        usd_amount=Decimal(usd),
        merchant="Test Shop",
    )


def _repayment(tx_id: str, date_str: str, eur: str, usd: str) -> RepaymentEvent:
    return RepaymentEvent(
        tx_id=tx_id,
        date=datetime.strptime(date_str, "%Y-%m-%d"),
        eur_amount=Decimal(eur),
        usd_amount=Decimal(usd),
    )


class TestComputeCardAnalysis:
    def test_balanced_usd_positive_spread(self) -> None:
        """Repay exactly the same USD but at worse rate → positive FX spread."""
        purchases = [_purchase("P1", "2025-03-01", "85", "100")]
        repayments = [_repayment("R1", "2025-04-01", "90", "100")]
        cashback_eur = Decimal("1.70")

        result = compute_card_analysis(2025, purchases, repayments, cashback_eur)

        assert result.total_purchase_eur == Decimal("85")
        assert result.total_purchase_usd == Decimal("100")
        assert result.total_repayment_eur == Decimal("90")
        assert result.total_repayment_usd == Decimal("100")
        # FX spread: 90 - 85 = 5 EUR (no mismatch since USD balances)
        assert result.fx_spread_eur == Decimal("5")
        assert result.cashback_eur == Decimal("1.70")
        assert result.cashback_tax_eur == Decimal("0.510")
        # net = 1.70 - 0.51 - 5 = -3.81
        assert result.net_benefit_eur == Decimal("-3.810")
        assert result.effective_rate_pct < 0

    def test_balanced_usd_favorable_spread(self) -> None:
        """Repay at better rate → negative FX spread (user saves money)."""
        purchases = [_purchase("P1", "2025-03-01", "90", "100")]
        repayments = [_repayment("R1", "2025-04-01", "85", "100")]
        cashback_eur = Decimal("1.80")

        result = compute_card_analysis(2025, purchases, repayments, cashback_eur)

        assert result.fx_spread_eur == Decimal("-5")
        # net = 1.80 - 0.54 - (-5) = 6.26
        assert result.net_benefit_eur == Decimal("6.260")
        assert result.effective_rate_pct > 0

    def test_usd_mismatch_partial_repayment(self) -> None:
        """Repay less USD than purchased → mismatch adjustment."""
        # Purchase: 1000 EUR / 1100 USD (rate = 1000/1100 ≈ 0.909)
        purchases = [_purchase("P1", "2025-03-01", "1000", "1100")]
        # Repay: 990 EUR / 1050 USD
        repayments = [_repayment("R1", "2025-04-01", "990", "1050")]
        cashback_eur = Decimal("20")

        result = compute_card_analysis(2025, purchases, repayments, cashback_eur)

        # Worked example from spec:
        # purchase_rate = 1000/1100 ≈ 0.9090909...
        # usd_mismatch = 1100 - 1050 = 50
        # mismatch_eur = 50 * 0.9090909... = 45.4545...
        # fx_spread = 990 - (1000 - 45.4545...) = 35.4545...
        assert result.fx_spread_eur > Decimal("35.45")
        assert result.fx_spread_eur < Decimal("35.46")
        # Tax = 20 * 0.30 = 6
        assert result.cashback_tax_eur == Decimal("6.0")
        # Net = 20 - 6 - fx_spread < 0
        assert result.net_benefit_eur < 0

    def test_no_purchases_no_repayments(self) -> None:
        """Year with no card activity."""
        result = compute_card_analysis(2025, [], [], Decimal("0"))

        assert result.total_purchase_eur == Decimal("0")
        assert result.total_repayment_eur == Decimal("0")
        assert result.fx_spread_eur == Decimal("0")
        assert result.net_benefit_eur == Decimal("0")
        assert result.effective_rate_pct == Decimal("0")

    def test_filters_by_year(self) -> None:
        """Only events from the target year are included."""
        purchases = [
            _purchase("P1", "2024-06-01", "85", "100"),
            _purchase("P2", "2025-03-01", "170", "200"),
        ]
        repayments = [
            _repayment("R1", "2024-07-01", "90", "100"),
            _repayment("R2", "2025-04-01", "175", "200"),
        ]

        result_2024 = compute_card_analysis(
            2024, purchases, repayments, Decimal("1.70")
        )
        assert result_2024.total_purchase_eur == Decimal("85")
        assert result_2024.total_repayment_eur == Decimal("90")

        result_2025 = compute_card_analysis(
            2025, purchases, repayments, Decimal("3.40")
        )
        assert result_2025.total_purchase_eur == Decimal("170")
        assert result_2025.total_repayment_eur == Decimal("175")

    def test_multiple_transactions(self) -> None:
        """Aggregate multiple purchases and repayments."""
        purchases = [
            _purchase("P1", "2025-01-15", "85", "100"),
            _purchase("P2", "2025-02-20", "170", "200"),
            _purchase("P3", "2025-03-10", "42.50", "50"),
        ]
        repayments = [
            _repayment("R1", "2025-02-01", "88", "100"),
            _repayment("R2", "2025-03-01", "177", "200"),
            _repayment("R3", "2025-04-01", "44", "50"),
        ]
        cashback_eur = Decimal("5.95")

        result = compute_card_analysis(2025, purchases, repayments, cashback_eur)

        assert result.total_purchase_eur == Decimal("297.50")
        assert result.total_purchase_usd == Decimal("350")
        assert result.total_repayment_eur == Decimal("309")
        assert result.total_repayment_usd == Decimal("350")
        # Balanced USD: fx_spread = 309 - 297.50 = 11.50
        assert result.fx_spread_eur == Decimal("11.50")

    def test_effective_rate_calculation(self) -> None:
        """Effective rate is net_benefit / purchase_eur * 100."""
        purchases = [_purchase("P1", "2025-03-01", "100", "110")]
        repayments = [_repayment("R1", "2025-04-01", "100", "110")]
        cashback_eur = Decimal("2")

        result = compute_card_analysis(2025, purchases, repayments, cashback_eur)

        # No FX spread (same rate), net = 2 - 0.6 = 1.4
        assert result.fx_spread_eur == Decimal("0")
        assert result.net_benefit_eur == Decimal("1.4")
        assert result.effective_rate_pct == Decimal("1.4")


class TestCardAnalysisParserIntegration:
    """Test that parser correctly creates CardPurchaseEvent and RepaymentEvent."""

    def test_card_purchase_parsed(self) -> None:
        import tempfile
        from pathlib import Path

        from nexo_tax.parser import parse_csv

        header = (
            "Transaction,Type,Input Currency,Input Amount,Output Currency,"
            "Output Amount,USD Equivalent,Fee,Fee Currency,Details,Date / Time (UTC)\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(header)
            f.write(
                'TX1,Nexo Card Purchase,USDX,-50.00000000,EUR,42.50000000,$50.00,-,-,'
                '"approved / CRV*Shop A",2025-06-15 10:00:00\n'
            )
            path = Path(f.name)

        result = parse_csv(path)
        assert len(result.card_purchase_events) == 1
        ev = result.card_purchase_events[0]
        assert ev.tx_id == "TX1"
        assert ev.eur_amount == Decimal("42.50000000")
        assert ev.usd_amount == Decimal("50.00000000")
        assert ev.merchant == "CRV*Shop A"
        # Also creates FX observation
        assert len(result.fx_observations) == 1

    def test_exchange_liquidation_parsed(self) -> None:
        import tempfile
        from pathlib import Path

        from nexo_tax.parser import parse_csv

        header = (
            "Transaction,Type,Input Currency,Input Amount,Output Currency,"
            "Output Amount,USD Equivalent,Fee,Fee Currency,Details,Date / Time (UTC)\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(header)
            f.write(
                "TX2,Exchange Liquidation,EURX,-45.00000000,"
                "USDX,50.00000000,$50.00,-,-,"
                '"approved / Exchange",2025-06-20 14:00:00\n'
            )
            path = Path(f.name)

        result = parse_csv(path)
        assert len(result.repayment_events) == 1
        ev = result.repayment_events[0]
        assert ev.tx_id == "TX2"
        assert ev.eur_amount == Decimal("45.00000000")
        assert ev.usd_amount == Decimal("50.00000000")

    def test_exchange_liquidation_eur_input(self) -> None:
        """Exchange Liquidation with EUR (not EURX) input currency."""
        import tempfile
        from pathlib import Path

        from nexo_tax.parser import parse_csv

        header = (
            "Transaction,Type,Input Currency,Input Amount,Output Currency,"
            "Output Amount,USD Equivalent,Fee,Fee Currency,Details,Date / Time (UTC)\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(header)
            f.write(
                'TX3,Exchange Liquidation,EUR,-30.00000000,xUSD,33.00000000,$33.00,-,-,'
                '"approved / Exchange",2025-07-01 10:00:00\n'
            )
            path = Path(f.name)

        result = parse_csv(path)
        assert len(result.repayment_events) == 1
        ev = result.repayment_events[0]
        assert ev.eur_amount == Decimal("30.00000000")
        assert ev.usd_amount == Decimal("33.00000000")

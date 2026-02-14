import tempfile
from decimal import Decimal
from pathlib import Path

from nexo_tax.calculator import build_lot_queue, compute_annual_summary
from nexo_tax.fx import FxRateTable
from nexo_tax.parser import parse_csv, parse_csvs

CSV_HEADER = (
    "Transaction,Type,Input Currency,Input Amount,Output Currency,"
    'Output Amount,USD Equivalent,Fee,Fee Currency,Details,Date / Time (UTC)\n'
)


def _write_csv(rows: list[str]) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(CSV_HEADER)
        for row in rows:
            f.write(row + "\n")
    return Path(f.name)


class TestEndToEnd:
    def test_full_pipeline(self) -> None:
        """Simulate: card purchases, cashback, interest, exchange buy, disposal."""
        path = _write_csv([
            # Card purchases (FX observations): rate ~0.85
            'P1,Nexo Card Purchase,xUSD,-100.00000000,EUR,85.00000000,$100.00,-,-,'
            '"approved / Shop A",2025-03-01 10:00:00',
            'P2,Nexo Card Purchase,xUSD,-50.00000000,EUR,42.50000000,$50.00,-,-,'
            '"approved / Shop B",2025-06-01 10:00:00',
            # Cashback events
            'C1,Cashback,NEXO,10.00000000,NEXO,10.00000000,$2.00,-,-,'
            '"approved / Shop A",2025-03-01 10:05:00',
            'C2,Cashback,NEXO,5.00000000,NEXO,5.00000000,$1.00,-,-,'
            '"approved / Shop B",2025-06-01 10:05:00',
            # Interest (NEXO)
            'I1,Interest,NEXO,1.00000000,NEXO,1.00000000,$0.50,-,-,'
            '"approved / NEXO Interest Earned",2025-04-01 06:00:00',
            # Interest (BTC) — now creates BTC lots
            'I2,Interest,BTC,0.00010000,BTC,0.00010000,$4.00,-,-,'
            '"approved / BTC Interest Earned",2025-05-01 06:00:00',
            # Exchange buy: buy 20 NEXO with EURX
            'B1,Exchange,EURX,-20.00000000,NEXO,20.00000000,$21.00,-,-,'
            '"approved / Exchange EURX to NEXO Token",2025-02-01 10:00:00',
            # Disposal: sell 12 NEXO for $10
            'D1,Exchange,NEXO,-12.00000000,BTC,0.00100000,$10.00,-,-,'
            '"approved / Exchange NEXO Token to Bitcoin",2025-09-01 10:00:00',
            # Unrelated row (should be skipped)
            'X1,Interest,NEXO,-0.01000000,-,0.00000000,$0.01,-,-,'
            '"approved / interest charge",2025-06-15 10:00:00',
        ])

        # Parse
        result = parse_csv(path)
        assert len(result.cashback_events) == 2
        assert len(result.interest_events) == 2  # NEXO + BTC
        assert len(result.exchange_buy_events) == 2  # EURX→NEXO + NEXO→BTC buy side
        assert len(result.fx_observations) == 2
        assert len(result.disposal_events) == 1

        # Build FX and apply EUR values
        fx = FxRateTable(result.fx_observations)
        for ev in result.cashback_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.interest_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.exchange_buy_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.disposal_events:
            ev.proceeds_eur = fx.convert_usd_to_eur(ev.proceeds_usd, ev.date)

        # C1: $2.00 * 0.85 = 1.70 EUR
        assert result.cashback_events[0].value_eur == Decimal("1.70")
        # NEXO Interest: $0.50 * 0.85 = 0.425 EUR
        assert result.interest_events[0].value_eur == Decimal("0.425")
        # BTC Interest: $4.00 * 0.85 = 3.40 EUR
        assert result.interest_events[1].value_eur == Decimal("3.40")
        assert result.interest_events[1].asset == "BTC"
        # Exchange buy (EURX→NEXO): $21 * 0.85 = 17.85 EUR
        assert result.exchange_buy_events[0].value_eur == Decimal("17.85")

        lots_by_asset = build_lot_queue(
            result.cashback_events, result.interest_events, result.exchange_buy_events
        )
        # NEXO FIFO order: B1(Feb), C1(Mar), I1(Apr), C2(Jun), D1-buy(Sep)
        nexo_lots = lots_by_asset["NEXO"]
        assert nexo_lots[0].tx_id == "B1"
        assert nexo_lots[1].tx_id == "C1"
        assert nexo_lots[2].tx_id == "I1"
        assert nexo_lots[3].tx_id == "C2"
        # BTC lots: I2(May), D1-buy(Sep)
        assert "BTC" in lots_by_asset
        btc_lots = lots_by_asset["BTC"]
        assert btc_lots[0].tx_id == "I2"

        summary = compute_annual_summary(
            2025,
            result.cashback_events,
            result.cashback_reversal_events,
            result.interest_events,
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )

        assert summary.total_cashback_events == 2
        assert summary.total_interest_events == 2  # NEXO + BTC
        assert summary.total_exchange_buy_events == 2
        assert len(summary.disposal_results) == 1

    def test_no_disposals(self) -> None:
        """Year with only cashback, no disposals."""
        path = _write_csv([
            'P1,Nexo Card Purchase,xUSD,-100.00000000,EUR,85.00000000,$100.00,-,-,'
            '"approved / Shop A",2025-03-01 10:00:00',
            'C1,Cashback,NEXO,10.00000000,NEXO,10.00000000,$2.00,-,-,'
            '"approved / Shop A",2025-03-01 10:05:00',
        ])

        result = parse_csv(path)
        fx = FxRateTable(result.fx_observations)
        for ev in result.cashback_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)

        lots_by_asset = build_lot_queue(result.cashback_events, [], [])
        summary = compute_annual_summary(
            2025, result.cashback_events, [], [], [], result.disposal_events,
            lots_by_asset,
        )

        assert summary.total_cashback_events == 1
        assert summary.total_cashback_eur == Decimal("1.70")
        assert len(summary.disposal_results) == 0
        assert summary.total_disposal_gain_eur == Decimal("0")
        assert summary.remaining_by_asset["NEXO"] == Decimal("10")

    def test_multi_year_lots_carry_forward(self) -> None:
        """2024 lots carry forward to 2025 disposal via FIFO."""
        path_2024 = _write_csv([
            # 2024 FX observation
            'P1,Nexo Card Purchase,USD,-100.00000000,EUR,90.00000000,$100.00,-,-,'
            '"approved / Shop",2024-08-01 10:00:00',
            # 2024 cashback: 20 NEXO worth $4 = 3.60 EUR
            'C1,Cashback,NEXO,20.00000000,NEXO,20.00000000,$4.00,-,-,'
            '"approved / Shop",2024-08-01 10:05:00',
        ])
        path_2025 = _write_csv([
            # 2025 FX observation
            'P2,Nexo Card Purchase,xUSD,-100.00000000,EUR,85.00000000,$100.00,-,-,'
            '"approved / Shop",2025-03-01 10:00:00',
            # 2025 cashback: 10 NEXO worth $2 = 1.70 EUR
            'C2,Cashback,NEXO,10.00000000,NEXO,10.00000000,$2.00,-,-,'
            '"approved / Shop",2025-03-01 10:05:00',
            # 2025 disposal: sell 25 NEXO for $20
            'D1,Exchange,NEXO,-25.00000000,BTC,0.00200000,$20.00,-,-,'
            '"approved / Exchange NEXO Token to Bitcoin",2025-09-01 10:00:00',
        ])

        result = parse_csvs([path_2024, path_2025])
        fx = FxRateTable(result.fx_observations)
        for ev in result.cashback_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.exchange_buy_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.disposal_events:
            ev.proceeds_eur = fx.convert_usd_to_eur(ev.proceeds_usd, ev.date)

        lots_by_asset = build_lot_queue(
            result.cashback_events, [], result.exchange_buy_events
        )

        # 2024: cashback only, no disposals
        summary_2024 = compute_annual_summary(
            2024,
            result.cashback_events,
            [],
            [],
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )
        assert summary_2024.total_cashback_events == 1
        assert summary_2024.total_cashback_eur == Decimal("3.60")
        assert len(summary_2024.disposal_results) == 0

        # 2025: disposal consumes 20 from 2024 lot + 5 from 2025 lot (FIFO)
        summary_2025 = compute_annual_summary(
            2025,
            result.cashback_events,
            [],
            [],
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )
        assert summary_2025.total_cashback_events == 1
        assert len(summary_2025.disposal_results) == 1
        dr = summary_2025.disposal_results[0]
        # Cost: 3.60 (all 20 from C1) + 1.70*(5/10) = 3.60 + 0.85 = 4.45
        assert dr.cost_basis_eur == Decimal("4.45")
        # Remaining: 5 NEXO (10 - 5 from C2)
        assert summary_2025.remaining_by_asset["NEXO"] == Decimal("5")

    def test_crypto_to_crypto_swap_pipeline(self) -> None:
        """BTC interest → BTC→ETH swap → ETH→EUR disposal."""
        path = _write_csv([
            # FX observation
            'P1,Nexo Card Purchase,xUSD,-100.00000000,EUR,85.00000000,$100.00,-,-,'
            '"approved / Shop",2025-01-01 10:00:00',
            # BTC interest: 0.01 BTC worth $400
            'I1,Interest,BTC,0.01000000,BTC,0.01000000,$400.00,-,-,'
            '"approved / BTC Interest",2025-02-01 06:00:00',
            # Swap BTC → ETH (disposal of BTC, acquisition of ETH)
            'S1,Exchange,BTC,-0.01000000,ETH,0.15000000,$500.00,-,-,'
            '"approved / Exchange Bitcoin to Ethereum",2025-06-01 10:00:00',
            # Sell ETH → EUR (disposal of ETH)
            'D1,Exchange,ETH,-0.15000000,EUR,600.00000000,$650.00,-,-,'
            '"approved / Exchange Ethereum to EUR",2025-09-01 10:00:00',
        ])

        result = parse_csv(path)
        # BTC→ETH creates both a disposal (BTC) and exchange buy (ETH)
        assert len(result.disposal_events) == 2  # BTC disposal + ETH disposal
        assert len(result.exchange_buy_events) == 1  # ETH buy from swap

        fx = FxRateTable(result.fx_observations)
        for ev in result.interest_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.exchange_buy_events:
            ev.value_eur = fx.convert_usd_to_eur(ev.value_usd, ev.date)
        for ev in result.disposal_events:
            ev.proceeds_eur = fx.convert_usd_to_eur(ev.proceeds_usd, ev.date)

        lots_by_asset = build_lot_queue(
            [], result.interest_events, result.exchange_buy_events
        )

        # BTC lots: interest (0.01 BTC @ 340 EUR)
        assert "BTC" in lots_by_asset
        assert lots_by_asset["BTC"][0].quantity == Decimal("0.01000000")
        # ETH lots: exchange buy (0.15 ETH @ 425 EUR)
        assert "ETH" in lots_by_asset
        assert lots_by_asset["ETH"][0].quantity == Decimal("0.15000000")

        summary = compute_annual_summary(
            2025,
            [],
            [],
            result.interest_events,
            result.exchange_buy_events,
            result.disposal_events,
            lots_by_asset,
        )

        assert len(summary.disposal_results) == 2
        # BTC disposal: proceeds = $500 * 0.85 = 425, cost = $400 * 0.85 = 340
        btc_dr = summary.disposal_results[0]
        assert btc_dr.disposal.asset == "BTC"
        assert btc_dr.cost_basis_eur == Decimal("340")
        assert btc_dr.gain_eur == Decimal("85")  # 425 - 340
        # ETH disposal: proceeds = $650 * 0.85 = 552.50, cost = $500 * 0.85 = 425
        eth_dr = summary.disposal_results[1]
        assert eth_dr.disposal.asset == "ETH"
        assert eth_dr.cost_basis_eur == Decimal("425")
        assert eth_dr.gain_eur == Decimal("127.50")  # 552.50 - 425
        # All lots consumed
        assert summary.remaining_lots == 0

import tempfile
from decimal import Decimal
from pathlib import Path

from nexo_tax.parser import _extract_merchant, _parse_usd, parse_csv, parse_csvs

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


class TestParseUsd:
    def test_strips_dollar_sign(self) -> None:
        assert _parse_usd("$1.23") == Decimal("1.23")

    def test_no_dollar_sign(self) -> None:
        assert _parse_usd("4.56") == Decimal("4.56")


class TestExtractMerchant:
    def test_strips_approved_prefix(self) -> None:
        assert _extract_merchant("approved / Wolt Poland POL") == "Wolt Poland POL"

    def test_no_prefix(self) -> None:
        assert _extract_merchant("Some merchant") == "Some merchant"


class TestParseCsv:
    def test_parses_cashback(self) -> None:
        path = _write_csv([
            'TX1,Cashback,NEXO,2.50000000,NEXO,2.50000000,$2.30,-,-,'
            '"approved / CRV*Wolt Poland POL",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.cashback_events) == 1
        ev = result.cashback_events[0]
        assert ev.tx_id == "TX1"
        assert ev.amount_nexo == Decimal("2.50000000")
        assert ev.value_usd == Decimal("2.30")
        assert ev.merchant == "CRV*Wolt Poland POL"

    def test_parses_card_purchase_xusd_as_fx(self) -> None:
        path = _write_csv([
            'TX2,Nexo Card Purchase,xUSD,-10.00000000,EUR,8.50000000,$10.00,-,-,'
            '"approved / CRV*Shop",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.fx_observations) == 1
        obs = result.fx_observations[0]
        assert obs.usd_amount == Decimal("10.00000000")
        assert obs.eur_amount == Decimal("8.50000000")

    def test_parses_card_purchase_usdx_as_fx(self) -> None:
        path = _write_csv([
            'TX2B,Nexo Card Purchase,USDX,-20.00000000,EUR,17.00000000,$20.00,-,-,'
            '"approved / CRV*Shop B",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.fx_observations) == 1
        obs = result.fx_observations[0]
        assert obs.usd_amount == Decimal("20.00000000")
        assert obs.eur_amount == Decimal("17.00000000")

    def test_parses_card_purchase_usd_as_fx(self) -> None:
        path = _write_csv([
            'TX2C,Nexo Card Purchase,USD,-30.00000000,EUR,25.50000000,$30.00,-,-,'
            '"approved / CRV*Shop C",2024-08-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.fx_observations) == 1
        obs = result.fx_observations[0]
        assert obs.usd_amount == Decimal("30.00000000")
        assert obs.eur_amount == Decimal("25.50000000")

    def test_parses_exchange_disposal(self) -> None:
        path = _write_csv([
            'TX3,Exchange,NEXO,-487.00000000,BTC,0.00488461,$511.68,-,-,'
            '"approved / Exchange NEXO Token to Bitcoin",2025-11-11 07:58:24',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        ev = result.disposal_events[0]
        assert ev.tx_id == "TX3"
        assert ev.asset == "NEXO"
        assert ev.quantity == Decimal("487.00000000")
        assert ev.proceeds_usd == Decimal("511.68")
        # Crypto-to-crypto also creates an exchange buy for the output
        assert len(result.exchange_buy_events) == 1
        buy = result.exchange_buy_events[0]
        assert buy.asset == "BTC"
        assert buy.amount == Decimal("0.00488461")

    def test_parses_nexo_interest(self) -> None:
        path = _write_csv([
            'TX4,Interest,NEXO,1.00000000,NEXO,1.00000000,$0.90,-,-,'
            '"approved / Interest",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.interest_events) == 1
        ev = result.interest_events[0]
        assert ev.asset == "NEXO"
        assert ev.amount == Decimal("1.00000000")

    def test_parses_btc_interest(self) -> None:
        path = _write_csv([
            'TX5,Interest,BTC,0.00010000,BTC,0.00010000,$4.00,-,-,'
            '"approved / Interest",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.interest_events) == 1
        ev = result.interest_events[0]
        assert ev.asset == "BTC"
        assert ev.amount == Decimal("0.00010000")
        assert ev.value_usd == Decimal("4.00")

    def test_parses_usdt_interest(self) -> None:
        path = _write_csv([
            'TX6,Fixed Term Interest,USDT,1.20000000,USDT,1.20000000,$1.20,-,-,'
            '"approved / Fixed Term Interest",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.interest_events) == 1
        ev = result.interest_events[0]
        assert ev.asset == "USDT"
        assert ev.source == "Fixed Term Interest"

    def test_parses_fiat_to_crypto_exchange_buy(self) -> None:
        """EURX → BTC creates an ExchangeBuyEvent(asset='BTC')."""
        path = _write_csv([
            'TX7,Exchange,EURX,-500.00000000,BTC,0.01000000,$530.00,-,-,'
            '"approved / Exchange EURX to Bitcoin",2025-07-01 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.exchange_buy_events) == 1
        ev = result.exchange_buy_events[0]
        assert ev.asset == "BTC"
        assert ev.amount == Decimal("0.01000000")
        assert ev.spent_currency == "EURX"
        assert ev.spent_amount == Decimal("500.00000000")
        # Fiat input → no disposal
        assert len(result.disposal_events) == 0

    def test_parses_crypto_to_fiat_disposal(self) -> None:
        """BTC → EUR creates a DisposalEvent(asset='BTC'), no exchange buy."""
        path = _write_csv([
            'TX8,Exchange,BTC,-0.01000000,EUR,500.00000000,$530.00,-,-,'
            '"approved / Exchange Bitcoin to EUR",2025-08-01 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        ev = result.disposal_events[0]
        assert ev.asset == "BTC"
        assert ev.quantity == Decimal("0.01000000")
        # Fiat output → no exchange buy
        assert len(result.exchange_buy_events) == 0

    def test_parses_crypto_to_crypto_swap(self) -> None:
        """BTC → ETH creates both a DisposalEvent(BTC) and ExchangeBuyEvent(ETH)."""
        path = _write_csv([
            'TX9,Exchange,BTC,-0.50000000,ETH,8.00000000,$20000.00,-,-,'
            '"approved / Exchange Bitcoin to Ethereum",2025-09-01 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        disp = result.disposal_events[0]
        assert disp.asset == "BTC"
        assert disp.quantity == Decimal("0.50000000")

        assert len(result.exchange_buy_events) == 1
        buy = result.exchange_buy_events[0]
        assert buy.asset == "ETH"
        assert buy.amount == Decimal("8.00000000")

    def test_parses_cashback_reversal(self) -> None:
        """Nexo Card Cashback Reversal creates a CashbackReversalEvent."""
        path = _write_csv([
            'TX10,Nexo Card Cashback Reversal,USD,-3.76000000,EUR,3.59,$3.76,-,-,'
            '"approved",2024-12-23 00:16:35',
        ])
        result = parse_csv(path)
        assert len(result.cashback_reversal_events) == 1
        ev = result.cashback_reversal_events[0]
        assert ev.tx_id == "TX10"
        assert ev.value_usd == Decimal("3.76")
        # No cashback or disposal created
        assert len(result.cashback_events) == 0
        assert len(result.disposal_events) == 0

    def test_parses_exchange_collateral(self) -> None:
        """Exchange Collateral (USDT→USDC) creates disposal + exchange buy."""
        path = _write_csv([
            'TX11,Exchange Collateral,USDT,-2803.11045400,USDC,2802.26977300,'
            '$2801.96,-,-,'
            '"approved / Collateral Exchange Tether to USD Coin",2025-03-12 20:23:26',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        disp = result.disposal_events[0]
        assert disp.asset == "USDT"
        assert disp.quantity == Decimal("2803.11045400")

        assert len(result.exchange_buy_events) == 1
        buy = result.exchange_buy_events[0]
        assert buy.asset == "USDC"
        assert buy.amount == Decimal("2802.26977300")

    def test_skips_fiat_interest(self) -> None:
        """Interest on fiat currencies should not create lots."""
        path = _write_csv([
            'TX_USDX,Interest,USDX,0.50000000,USDX,0.50000000,$0.50,-,-,'
            '"approved / Interest",2025-06-15 10:00:00',
            'TX_XUSD,Interest,xUSD,0.30000000,xUSD,0.30000000,$0.30,-,-,'
            '"approved / Interest",2025-06-15 11:00:00',
            'TX_EURX,Interest,EURX,0.20000000,EURX,0.20000000,$0.21,-,-,'
            '"approved / Interest",2025-06-15 12:00:00',
        ])
        result = parse_csv(path)
        assert len(result.interest_events) == 0

    def test_parses_manual_sell_order_crypto(self) -> None:
        """Manual Sell Order for crypto creates a DisposalEvent."""
        path = _write_csv([
            'TX_MSO,Manual Sell Order,USDT,-51.67888500,USDT,0.00000000,$51.46,-,-,'
            '"approved / Crypto Repayment",2025-11-05 07:09:16',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        ev = result.disposal_events[0]
        assert ev.tx_id == "TX_MSO"
        assert ev.asset == "USDT"
        assert ev.quantity == Decimal("51.67888500")
        assert ev.proceeds_usd == Decimal("51.46")
        assert ev.description == "Crypto Repayment"

    def test_skips_manual_sell_order_fiat(self) -> None:
        """Manual Sell Order for fiat (EURX, USDX) should not create disposal."""
        path = _write_csv([
            'TX_MSO2,Manual Sell Order,EURX,-62.03000000,EURX,0.00000000,$64.58,-,-,'
            '"approved / Crypto Repayment",2024-12-31 11:58:38',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 0

    def test_parses_top_up_crypto(self) -> None:
        """Top up Crypto creates an ExchangeBuyEvent."""
        path = _write_csv([
            'TX_TOP,Top up Crypto,USDT,10.06467500,USDT,10.06467500,$10.07,-,-,'
            '"approved / 0xabc123",2024-08-28 07:44:40',
        ])
        result = parse_csv(path)
        assert len(result.exchange_buy_events) == 1
        ev = result.exchange_buy_events[0]
        assert ev.tx_id == "TX_TOP"
        assert ev.asset == "USDT"
        assert ev.amount == Decimal("10.06467500")
        assert ev.value_usd == Decimal("10.07")

    def test_parses_withdrawal(self) -> None:
        """Withdrawal creates a DisposalEvent."""
        path = _write_csv([
            'TX_WD,Withdrawal,NEXO,-20.00000000,NEXO,20.00000000,$26.64,-,-,'
            '"approved / NEXO withdrawal",2024-12-26 09:15:30',
        ])
        result = parse_csv(path)
        assert len(result.disposal_events) == 1
        ev = result.disposal_events[0]
        assert ev.tx_id == "TX_WD"
        assert ev.asset == "NEXO"
        assert ev.quantity == Decimal("20.00000000")
        assert ev.proceeds_usd == Decimal("26.64")
        assert ev.description == "NEXO withdrawal"

    def test_skips_unrelated_types(self) -> None:
        path = _write_csv([
            'TX4,Interest,NEXO,1.00000000,NEXO,1.00000000,$0.90,-,-,'
            '"approved / Interest",2025-06-15 10:00:00',
        ])
        result = parse_csv(path)
        assert len(result.cashback_events) == 0
        assert len(result.fx_observations) == 0
        assert len(result.disposal_events) == 0

    def test_sorts_by_date_ascending(self) -> None:
        path = _write_csv([
            'TX_LATE,Cashback,NEXO,1.00000000,NEXO,1.00000000,$1.00,-,-,'
            '"approved / Late",2025-12-01 10:00:00',
            'TX_EARLY,Cashback,NEXO,2.00000000,NEXO,2.00000000,$2.00,-,-,'
            '"approved / Early",2025-01-01 10:00:00',
        ])
        result = parse_csv(path)
        assert result.cashback_events[0].tx_id == "TX_EARLY"
        assert result.cashback_events[1].tx_id == "TX_LATE"

    def test_parse_csvs_merges_and_sorts(self) -> None:
        path1 = _write_csv([
            'TX_2025,Cashback,NEXO,1.00000000,NEXO,1.00000000,$1.00,-,-,'
            '"approved / Shop 2025",2025-03-01 10:00:00',
        ])
        path2 = _write_csv([
            'TX_2024,Cashback,NEXO,2.00000000,NEXO,2.00000000,$2.00,-,-,'
            '"approved / Shop 2024",2024-08-01 10:00:00',
        ])
        result = parse_csvs([path1, path2])
        assert len(result.cashback_events) == 2
        assert result.cashback_events[0].tx_id == "TX_2024"
        assert result.cashback_events[1].tx_id == "TX_2025"

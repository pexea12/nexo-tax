from datetime import datetime
from decimal import Decimal

from nexo_tax.fx import FxRateTable, build_daily_rates
from nexo_tax.parser import FxObservation


def _obs(date_str: str, eur: str, usd: str) -> FxObservation:
    return FxObservation(
        date=datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S"),
        eur_amount=Decimal(eur),
        usd_amount=Decimal(usd),
    )


class TestBuildDailyRates:
    def test_single_observation(self) -> None:
        obs = [_obs("2025-06-15 10:00:00", "85", "100")]
        rates = build_daily_rates(obs)
        assert len(rates) == 1
        assert rates[datetime(2025, 6, 15).date()] == Decimal("85") / Decimal("100")

    def test_weighted_average_same_day(self) -> None:
        obs = [
            _obs("2025-06-15 10:00:00", "85", "100"),
            _obs("2025-06-15 14:00:00", "170", "200"),
        ]
        rates = build_daily_rates(obs)
        # Weighted: (85+170) / (100+200) = 255/300 = 0.85
        assert rates[datetime(2025, 6, 15).date()] == Decimal("255") / Decimal("300")


class TestFxRateTable:
    def test_exact_date_match(self) -> None:
        fx = FxRateTable([_obs("2025-06-15 10:00:00", "85", "100")])
        rate = fx.rate_for_date(datetime(2025, 6, 15, 12, 0, 0))
        assert rate == Decimal("85") / Decimal("100")

    def test_nearest_date_before(self) -> None:
        fx = FxRateTable([
            _obs("2025-06-10 10:00:00", "85", "100"),
            _obs("2025-06-20 10:00:00", "86", "100"),
        ])
        # June 12 is closer to June 10 than June 20
        rate = fx.rate_for_date(datetime(2025, 6, 12, 10, 0, 0))
        assert rate == Decimal("85") / Decimal("100")

    def test_nearest_date_after(self) -> None:
        fx = FxRateTable([
            _obs("2025-06-10 10:00:00", "85", "100"),
            _obs("2025-06-20 10:00:00", "86", "100"),
        ])
        # June 18 is closer to June 20 than June 10
        rate = fx.rate_for_date(datetime(2025, 6, 18, 10, 0, 0))
        assert rate == Decimal("86") / Decimal("100")

    def test_before_all_dates(self) -> None:
        fx = FxRateTable([_obs("2025-06-15 10:00:00", "85", "100")])
        rate = fx.rate_for_date(datetime(2025, 1, 1, 10, 0, 0))
        assert rate == Decimal("85") / Decimal("100")

    def test_after_all_dates(self) -> None:
        fx = FxRateTable([_obs("2025-06-15 10:00:00", "85", "100")])
        rate = fx.rate_for_date(datetime(2025, 12, 31, 10, 0, 0))
        assert rate == Decimal("85") / Decimal("100")

    def test_convert_usd_to_eur(self) -> None:
        fx = FxRateTable([_obs("2025-06-15 10:00:00", "85", "100")])
        eur = fx.convert_usd_to_eur(Decimal("10"), datetime(2025, 6, 15, 10, 0, 0))
        assert eur == Decimal("10") * Decimal("85") / Decimal("100")

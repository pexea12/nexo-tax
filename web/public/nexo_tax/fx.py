from bisect import bisect_left
from datetime import date, datetime
from decimal import Decimal

from nexo_tax.parser import FxObservation


def build_daily_rates(observations: list[FxObservation]) -> dict[date, Decimal]:
    """Build daily USD/EUR rates from card purchase observations.

    Multiple purchases on the same day are combined using a weighted average
    (total EUR / total USD).
    """
    daily_totals: dict[date, tuple[Decimal, Decimal]] = {}  # date -> (eur, usd)

    for obs in observations:
        day = obs.date.date()
        eur, usd = daily_totals.get(day, (Decimal("0"), Decimal("0")))
        daily_totals[day] = (eur + obs.eur_amount, usd + obs.usd_amount)

    return {day: eur / usd for day, (eur, usd) in daily_totals.items()}


class FxRateTable:
    """USD/EUR rate lookup with nearest-date fallback."""

    def __init__(self, observations: list[FxObservation]) -> None:
        self._rates = build_daily_rates(observations)
        self._sorted_dates = sorted(self._rates.keys())

    def rate_for_date(self, dt: datetime) -> Decimal:
        """Return USD/EUR rate for the given datetime.

        Uses nearest date if exact match unavailable.
        """
        day = dt.date()
        if day in self._rates:
            return self._rates[day]
        return self._nearest_rate(day)

    def _nearest_rate(self, day: date) -> Decimal:
        """Find rate from the nearest date using bisect."""
        if not self._sorted_dates:
            raise ValueError("No FX observations available")

        idx = bisect_left(self._sorted_dates, day)

        if idx == 0:
            return self._rates[self._sorted_dates[0]]
        if idx >= len(self._sorted_dates):
            return self._rates[self._sorted_dates[-1]]

        before = self._sorted_dates[idx - 1]
        after = self._sorted_dates[idx]
        if (day - before) <= (after - day):
            return self._rates[before]
        return self._rates[after]

    def convert_usd_to_eur(self, usd_amount: Decimal, dt: datetime) -> Decimal:
        """Convert a USD amount to EUR using the rate for the given date."""
        rate = self.rate_for_date(dt)
        return usd_amount * rate

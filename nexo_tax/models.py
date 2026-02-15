from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class CashbackEvent:
    tx_id: str
    date: datetime
    amount_nexo: Decimal
    value_usd: Decimal
    value_eur: Decimal
    merchant: str


@dataclass
class CashbackReversalEvent:
    """Reversal of a previous cashback when a card purchase is refunded."""

    tx_id: str
    date: datetime
    value_usd: Decimal
    value_eur: Decimal


@dataclass
class InterestEvent:
    tx_id: str
    date: datetime
    asset: str
    amount: Decimal
    value_usd: Decimal
    value_eur: Decimal
    source: str  # "Interest", "Fixed Term Interest", "Exchange Cashback"


@dataclass
class ExchangeBuyEvent:
    """Crypto purchased via Exchange (e.g. EURX → NEXO, EUR → BTC)."""

    tx_id: str
    date: datetime
    asset: str
    amount: Decimal
    spent_amount: Decimal
    spent_currency: str
    value_usd: Decimal
    value_eur: Decimal


@dataclass
class Lot:
    asset: str
    acquired_date: datetime
    quantity: Decimal
    cost_eur: Decimal
    remaining: Decimal
    tx_id: str
    source: str = "cashback"  # "cashback", "interest", "exchange_buy"


@dataclass
class DisposalEvent:
    tx_id: str
    date: datetime
    asset: str
    quantity: Decimal
    proceeds_usd: Decimal
    proceeds_eur: Decimal
    fee_eur: Decimal
    description: str


@dataclass
class DisposalResult:
    disposal: DisposalEvent
    cost_basis_eur: Decimal
    gain_eur: Decimal
    lots_consumed: list[tuple[str, Decimal, Decimal, datetime]]  # (tx_id, qty_used, cost_eur, acquired_date)


@dataclass
class RepaymentEvent:
    """Exchange Liquidation: EURX → USDX to repay credit line."""

    tx_id: str
    date: datetime
    eur_amount: Decimal  # EURX input amount
    usd_amount: Decimal  # USDX output amount


@dataclass
class CardPurchaseEvent:
    """Nexo Card Purchase: USDX → EUR at point of sale."""

    tx_id: str
    date: datetime
    eur_amount: Decimal  # EUR output amount
    usd_amount: Decimal  # USDX input amount
    merchant: str


@dataclass
class CardAnalysisSummary:
    """Profitability analysis of card cashback vs FX spread costs."""

    year: int
    total_purchase_eur: Decimal
    total_purchase_usd: Decimal
    total_repayment_eur: Decimal
    total_repayment_usd: Decimal
    fx_spread_eur: Decimal  # extra EUR paid due to FX
    cashback_eur: Decimal  # net cashback value
    cashback_tax_eur: Decimal  # 30% capital income tax
    net_benefit_eur: Decimal  # cashback - tax - fx_spread
    effective_rate_pct: Decimal  # net_benefit / purchase_eur * 100


@dataclass
class AnnualSummary:
    year: int
    total_cashback_events: int
    total_cashback_nexo: Decimal
    total_cashback_eur: Decimal
    total_cashback_reversal_events: int
    total_cashback_reversal_eur: Decimal
    total_interest_events: int
    total_interest_by_asset: dict[str, Decimal]
    total_interest_eur: Decimal
    total_exchange_buy_events: int
    total_exchange_buy_by_asset: dict[str, Decimal]
    total_exchange_buy_eur: Decimal
    disposal_results: list[DisposalResult]
    total_disposal_proceeds_eur: Decimal
    total_disposal_cost_basis_eur: Decimal
    total_disposal_gain_eur: Decimal
    remaining_lots: int
    remaining_by_asset: dict[str, Decimal]

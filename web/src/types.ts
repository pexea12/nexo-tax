export interface DisposalResult {
  tx_id: string
  date: string
  asset: string
  quantity: string
  proceeds_eur: string
  fee_eur: string
  cost_basis_eur: string
  gain_eur: string
  description: string
  acquired_range: string
}

export interface AnnualSummary {
  year: number
  total_cashback_events: number
  total_cashback_nexo: string
  total_cashback_eur: string
  total_cashback_reversal_events: number
  total_cashback_reversal_eur: string
  net_cashback_eur: string
  total_interest_events: number
  total_interest_by_asset: Record<string, string>
  total_interest_eur: string
  total_capital_income_eur: string
  total_exchange_buy_events: number
  total_exchange_buy_by_asset: Record<string, string>
  total_exchange_buy_eur: string
  disposals: DisposalResult[]
  total_disposal_proceeds_eur: string
  total_disposal_cost_basis_eur: string
  total_disposal_gain_eur: string
  remaining_lots: number
  remaining_by_asset: Record<string, string>
}

export interface CardAnalysis {
  year: number
  total_purchase_eur: string
  total_purchase_usd: string
  total_repayment_eur: string
  total_repayment_usd: string
  fx_spread_eur: string
  cashback_eur: string
  cashback_tax_eur: string
  net_benefit_eur: string
  effective_rate_pct: string
}

export interface YearResult {
  year: number
  summary: AnnualSummary
  card_analysis: CardAnalysis
}

export interface CalculationResult {
  console: string
  audit_files: Record<string, string>
  years: YearResult[]
}

export interface DetectedYears {
  [key: number]: boolean
}

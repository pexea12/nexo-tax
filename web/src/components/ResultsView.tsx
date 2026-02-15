import React from 'react'
import { YearResult, AnnualSummary, CardAnalysis, DisposalResult } from '../types'

interface ResultsViewProps {
  years: YearResult[]
}

function eur(val: string) {
  return `€${parseFloat(val).toLocaleString('en-IE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function usd(val: string) {
  return `$${parseFloat(val).toLocaleString('en-IE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function gainColor(val: string) {
  const n = parseFloat(val)
  if (n > 0) return '#4caf50'
  if (n < 0) return '#f44336'
  return 'inherit'
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h4 style={{
        margin: '0 0 0.75rem 0',
        fontSize: '0.85em',
        fontWeight: 600,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: '#999',
        borderBottom: '1px solid #333',
        paddingBottom: '0.4rem',
      }}>{title}</h4>
      {children}
    </div>
  )
}

function Row({ label, value, valueStyle }: { label: string; value: React.ReactNode; valueStyle?: React.CSSProperties }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '0.25rem 0', gap: '1rem' }}>
      <span style={{ color: '#bbb', fontSize: '0.9em' }}>{label}</span>
      <span style={{ fontWeight: 500, fontVariantNumeric: 'tabular-nums', ...valueStyle }}>{value}</span>
    </div>
  )
}

function DisposalCard({ d }: { d: DisposalResult }) {
  return (
    <div style={{
      background: '#1e1e1e',
      border: '1px solid #333',
      borderRadius: '6px',
      padding: '0.75rem 1rem',
      marginBottom: '0.5rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
        <span style={{ fontWeight: 600 }}>{d.asset} — {d.description || 'Disposal'}</span>
        <span style={{ color: gainColor(d.gain_eur), fontWeight: 600 }}>
          {parseFloat(d.gain_eur) >= 0 ? '+' : ''}{eur(d.gain_eur)}
        </span>
      </div>
      <div style={{ fontSize: '0.85em', color: '#999', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.2rem 1rem' }}>
        <span>Sold: {d.date}</span>
        <span>Acquired: {d.acquired_range}</span>
        <span>Qty: {parseFloat(d.quantity).toFixed(8)} {d.asset}</span>
        <span>Proceeds: {eur(d.proceeds_eur)}</span>
        <span>Cost basis: {eur(d.cost_basis_eur)}</span>
        {parseFloat(d.fee_eur) > 0 && <span>Fee: {eur(d.fee_eur)}</span>}
      </div>
    </div>
  )
}

function SummaryPanel({ summary }: { summary: AnnualSummary }) {
  const hasReversals = summary.total_cashback_reversal_events > 0
  const hasDisposals = summary.disposals.length > 0
  const hasExchangeBuys = summary.total_exchange_buy_events > 0

  return (
    <>
      <Section title="Capital Income (report in MyTax → Other capital income)">
        <Row label="Cashback events" value={summary.total_cashback_events} />
        <Row label="NEXO received" value={`${parseFloat(summary.total_cashback_nexo).toFixed(8)} NEXO`} />
        <Row label="Cashback value" value={eur(summary.total_cashback_eur)} />
        {hasReversals && <>
          <Row label="Cashback reversals" value={summary.total_cashback_reversal_events} />
          <Row label="Reversed amount" value={`−${eur(summary.total_cashback_reversal_eur)}`} />
          <Row label="Net cashback" value={eur(summary.net_cashback_eur)} />
        </>}
        <Row label="Interest events" value={summary.total_interest_events} />
        {Object.entries(summary.total_interest_by_asset).map(([asset, qty]) => (
          <Row key={asset} label={`  ${asset} received`} value={`${parseFloat(qty).toFixed(8)} ${asset}`} />
        ))}
        <Row label="Interest value" value={eur(summary.total_interest_eur)} />
        <Row
          label="TOTAL CAPITAL INCOME"
          value={eur(summary.total_capital_income_eur)}
          valueStyle={{ fontSize: '1.1em', color: '#ffd700' }}
        />
      </Section>

      {hasExchangeBuys && (
        <Section title="Crypto Purchases (not taxable — creates FIFO lots)">
          <Row label="Purchase events" value={summary.total_exchange_buy_events} />
          {Object.entries(summary.total_exchange_buy_by_asset).map(([asset, qty]) => (
            <Row key={asset} label={`  ${asset} acquired`} value={`${parseFloat(qty).toFixed(8)} ${asset}`} />
          ))}
          <Row label="Total cost" value={eur(summary.total_exchange_buy_eur)} />
        </Section>
      )}

      <Section title="Capital Gains / Losses (report in MyTax → Capital gains – Crypto assets)">
        {hasDisposals ? (
          <>
            {summary.disposals.map((d) => <DisposalCard key={d.tx_id} d={d} />)}
            <div style={{ marginTop: '0.75rem' }}>
              <Row label="Total proceeds" value={eur(summary.total_disposal_proceeds_eur)} />
              <Row label="Total cost basis" value={eur(summary.total_disposal_cost_basis_eur)} />
              <Row
                label="NET GAIN / LOSS"
                value={`${parseFloat(summary.total_disposal_gain_eur) >= 0 ? '+' : ''}${eur(summary.total_disposal_gain_eur)}`}
                valueStyle={{ fontSize: '1.1em', color: gainColor(summary.total_disposal_gain_eur) }}
              />
            </div>
          </>
        ) : (
          <p style={{ color: '#999', fontSize: '0.9em', margin: 0 }}>No disposals this year.</p>
        )}
      </Section>

      <Section title="Lot Queue Status">
        <Row label="Remaining lots" value={summary.remaining_lots} />
        {Object.entries(summary.remaining_by_asset).map(([asset, qty]) => (
          <Row key={asset} label={`  ${asset}`} value={`${parseFloat(qty).toFixed(8)} ${asset}`} />
        ))}
      </Section>
    </>
  )
}

function CardAnalysisPanel({ card }: { card: CardAnalysis }) {
  const hasPurchases = parseFloat(card.total_purchase_eur) > 0
  if (!hasPurchases) return null

  const netPositive = parseFloat(card.net_benefit_eur) >= 0

  return (
    <>
      <Section title="Card Purchases">
        <Row label="Total EUR spent" value={eur(card.total_purchase_eur)} />
        <Row label="Total USD charged" value={usd(card.total_purchase_usd)} />
      </Section>
      <Section title="Credit Line Repayments">
        <Row label="Total EUR" value={eur(card.total_repayment_eur)} />
        <Row label="Total USD" value={usd(card.total_repayment_usd)} />
      </Section>
      <Section title="Card Profitability">
        <Row label="FX spread cost" value={`−${eur(card.fx_spread_eur)}`} />
        <Row label="Cashback earned" value={`+${eur(card.cashback_eur)}`} />
        <Row label="Tax on cashback (30%)" value={`−${eur(card.cashback_tax_eur)}`} />
        <Row
          label="NET BENEFIT"
          value={`${netPositive ? '+' : ''}${eur(card.net_benefit_eur)}`}
          valueStyle={{ fontSize: '1.1em', color: gainColor(card.net_benefit_eur) }}
        />
        <Row label="Effective cashback rate" value={`${parseFloat(card.effective_rate_pct).toFixed(2)}%`} />
      </Section>
    </>
  )
}

export default function ResultsView({ years }: ResultsViewProps) {
  if (years.length === 0) return null

  return (
    <div style={{ marginTop: '2rem', textAlign: 'left' }}>
      <h3 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Tax Summary</h3>
      {years.map(({ year, summary, card_analysis }) => (
        <div key={year} style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          borderRadius: '10px',
          padding: '1.5rem',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{
            margin: '0 0 1.5rem 0',
            fontSize: '1.3em',
            borderBottom: '2px solid #444',
            paddingBottom: '0.5rem',
          }}>
            Finnish Crypto Tax — {year}
          </h3>
          <SummaryPanel summary={summary} />
          <h4 style={{
            margin: '1.5rem 0 1rem 0',
            fontSize: '1.1em',
            borderBottom: '1px solid #333',
            paddingBottom: '0.4rem',
          }}>
            Card Cashback Profitability — {year}
          </h4>
          <CardAnalysisPanel card={card_analysis} />
        </div>
      ))}
    </div>
  )
}

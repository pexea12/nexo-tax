import React, { useState } from 'react'

interface PanelProps {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}

function Panel({ title, children, defaultOpen = false }: PanelProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div style={{
      border: '1px solid #2a2a2a',
      borderRadius: '8px',
      marginBottom: '0.75rem',
      overflow: 'hidden',
    }}>
      <h3 style={{ margin: 0 }}>
        <button
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          style={{
            width: '100%',
            background: '#161616',
            border: 'none',
            padding: '0.9rem 1.25rem',
            textAlign: 'left',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.95em',
            fontWeight: 600,
            color: '#eee',
          }}
        >
          <span>{title}</span>
          <span style={{ color: '#666', fontSize: '0.85em', marginLeft: '0.5rem', flexShrink: 0 }} aria-hidden="true">
            {open ? '▲' : '▼'}
          </span>
        </button>
      </h3>
      {open && (
        <div style={{
          padding: '1rem 1.25rem 1.25rem',
          background: '#111',
          fontSize: '0.9em',
          lineHeight: 1.7,
          color: '#ccc',
        }}>
          {children}
        </div>
      )}
    </div>
  )
}

function Callout({ children, color = '#ffd700' }: { children: React.ReactNode; color?: string }) {
  return (
    <div style={{
      borderLeft: `3px solid ${color}`,
      background: '#1a1a1a',
      padding: '0.6rem 0.9rem',
      borderRadius: '0 6px 6px 0',
      margin: '0.75rem 0',
      fontSize: '0.95em',
    }}>
      {children}
    </div>
  )
}

function Dt({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '0.25rem 0.75rem', marginBottom: '0.4rem' }}>
      <span style={{ color: '#888', whiteSpace: 'nowrap' }}>{label}</span>
      <span>{children}</span>
    </div>
  )
}

export default function InfoSection() {
  return (
    <div style={{ marginBottom: '2rem', textAlign: 'left' }}>
      <h2 style={{ fontSize: '1.1em', color: '#999', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        How it works
      </h2>

      <Panel title="Why use this tool instead of Koinly?" defaultOpen>
        <p style={{ marginTop: 0 }}>
          Nexo's own recommendation is to use <strong>Koinly</strong> for tax reporting — but Koinly has
          real limitations that make it a poor fit for Finnish Nexo cardholders:
        </p>
        <ul style={{ paddingLeft: '1.2rem', margin: '0.5rem 0' }}>
          <li>
            <strong>Transaction caps &amp; high cost</strong> — Koinly's free tier supports only up to
            10,000 transactions. If you use the Nexo card regularly you can exceed this quickly,
            forcing you onto paid plans that cost €49–€279 per year.
          </li>
          <li>
            <strong>Generic, not Finland-specific</strong> — Koinly is a general-purpose tool. It does
            not understand Nexo's cashback mechanics in detail or apply Finnish Vero rules
            (capital income vs. capital gains, FIFO lot matching) out of the box.
          </li>
          <li>
            <strong>No effective cashback rate</strong> — Koinly tells you your tax liability, but it
            cannot answer the most important question: <em>is the Nexo card actually worth using?</em>{' '}
            This tool calculates your true effective cashback rate after accounting for tax and FX spread costs.
          </li>
        </ul>
        <Callout color="#4caf50">
          This tool is <strong>free, open-source, and runs entirely in your browser</strong> — no account,
          no subscription, no data upload. Your CSV files never leave your device.
        </Callout>
      </Panel>

      <Panel title="What is the Nexo card and how does cashback work?">
        <p style={{ marginTop: 0 }}>
          The <strong>Nexo credit card</strong> lets you spend your crypto as collateral without selling it.
          Every purchase earns <strong>2% cashback in NEXO tokens</strong>.
        </p>
        <p>Here is what happens behind the scenes for each purchase:</p>
        <ol style={{ paddingLeft: '1.2rem', margin: '0.5rem 0' }}>
          <li>You pay in EUR at a merchant (e.g. €100 groceries).</li>
          <li>Nexo settles in USD (e.g. $105), adding its own FX spread.</li>
          <li>Nexo credits 2% cashback in NEXO tokens calculated from the USD amount (e.g. $2.10 worth of NEXO).</li>
          <li>You later repay the credit line by converting EUR → USD inside Nexo.</li>
        </ol>
        <Callout>
          To receive 2% cashback you must hold at least <strong>€5,000 of crypto</strong> on Nexo
          with at least <strong>15% in NEXO tokens</strong>.
        </Callout>
        <p style={{ marginBottom: 0 }}>
          The tool also tracks <strong>interest income</strong> (Fixed Term Interest, Exchange Cashback)
          and any <strong>crypto disposals</strong> (selling, swapping, or spending crypto).
        </p>
      </Panel>

      <Panel title="Finnish taxation of Nexo cashback (Vero)">
        <p style={{ marginTop: 0 }}>
          Finland taxes Nexo cashback as <strong>capital income</strong>, not as a tax-free rebate.
          This is because the 2% rate depends on your existing crypto holdings — a condition
          that Vero classifies as <em>"income based on existing crypto assets"</em> (Case B).
        </p>

        <p style={{ fontWeight: 600, marginBottom: '0.4rem' }}>You need to report two things in MyTax (OmaVero):</p>

        <Callout color="#4caf50">
          <strong>1 — Other capital income</strong> (Muut pääomatulot)<br />
          The total EUR value of all NEXO cashback and interest received during the year.
          Taxed at <strong>30%</strong> (34% above €30,000).
        </Callout>

        <Callout color="#2196f3">
          <strong>2 — Capital gains — Crypto assets</strong> (Virtuaalivaluuttojen luovutukset)<br />
          For every disposal (selling, swapping, or spending NEXO or other crypto), report
          the proceeds, FIFO cost basis, and gain/loss.
          Taxed at <strong>30%</strong> on net gain (34% above €30,000).
        </Callout>

        <p>Key rules this tool applies:</p>
        <ul style={{ paddingLeft: '1.2rem', margin: '0.5rem 0' }}>
          <li><strong>FIFO</strong> — Finland uses First-In First-Out for crypto lot matching.</li>
          <li><strong>FX spread is not deductible</strong> — the extra EUR lost due to Nexo's USD conversion on card repayments is a private living cost, not a deductible investment expense.</li>
          <li><strong>Disposal fees are deductible</strong> — any fee charged when selling or swapping crypto reduces the gain.</li>
          <li><strong>Crypto-to-crypto swaps are taxable</strong> — e.g. swapping NEXO for BTC is a disposal of NEXO and creates a new BTC acquisition lot.</li>
        </ul>

        <p style={{ marginBottom: 0, color: '#888', fontSize: '0.88em' }}>
          This tool is for informational purposes. Verify your numbers with Vero or a tax advisor if unsure.
        </p>
      </Panel>

      <Panel title="What is the effective cashback rate?">
        <p style={{ marginTop: 0 }}>
          The headline <strong>"2% cashback"</strong> sounds attractive, but two hidden costs eat into it:
        </p>

        <Dt label="FX spread cost">
          Nexo converts EUR→USD at purchase time and USD→EUR at repayment time.
          Because these rates differ, you often pay <em>more EUR</em> to repay than the original purchase cost.
        </Dt>
        <Dt label="Tax on cashback">
          The NEXO cashback is capital income. At a 30% rate, €1 of cashback
          costs you €0.30 in tax — so you keep only €0.70.
        </Dt>

        <p>The formula this tool uses:</p>
        <div style={{
          background: '#1e1e1e',
          border: '1px solid #333',
          borderRadius: '6px',
          padding: '0.75rem 1rem',
          fontFamily: 'monospace',
          fontSize: '0.88em',
          lineHeight: 1.8,
          margin: '0.5rem 0',
        }}>
          net_benefit = cashback_eur − tax_on_cashback − fx_spread_eur<br />
          effective_rate = net_benefit ÷ total_purchase_eur × 100
        </div>

        <Callout color="#f44336">
          If the FX spread is large, the effective rate can be <strong>negative</strong> — meaning the
          card cost you money despite earning cashback. This is common when EUR/USD rates shift between
          purchase and repayment.
        </Callout>
        <p style={{ marginBottom: 0 }}>
          A positive effective rate means the card was genuinely profitable after all costs.
          Use this number to decide whether keeping the Nexo card makes financial sense.
        </p>
      </Panel>

      <Panel title="How to file in MyTax (OmaVero) — step by step">
        <ol style={{ paddingLeft: '1.2rem', margin: '0 0 0.75rem' }}>
          <li style={{ marginBottom: '0.5rem' }}>
            Run this calculator with your Nexo CSV export(s).
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Log in to <strong>OmaVero</strong> (vero.fi).
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Go to <strong>Capital income → Other capital income</strong> and enter the
            <em> Total Capital Income</em> figure from this tool.
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Go to <strong>Capital gains → Crypto assets</strong> and add each disposal
            (date, asset, proceeds, acquisition cost, gain/loss).
            Use the per-disposal breakdown shown in the results.
          </li>
          <li style={{ marginBottom: '0' }}>
            Keep the audit CSV files (download below the results) in case Vero requests documentation.
          </li>
        </ol>
        <Callout color="#ffd700">
          Both fields must be filled if applicable — missing one or the other is a common mistake.
        </Callout>
      </Panel>
    </div>
  )
}

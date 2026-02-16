export default function Footer() {
  return (
    <footer>
      <a
        href="https://buymeacoffee.com/pexea12"
        target="_blank"
        rel="noopener noreferrer"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          background: '#FFDD00',
          color: '#000',
          fontWeight: 700,
          fontSize: '0.95em',
          padding: '0.55rem 1.25rem',
          borderRadius: '8px',
          textDecoration: 'none',
          marginBottom: '1rem',
        }}
      >
        <span aria-hidden="true">☕</span> Buy me a coffee
      </a>
      <p style={{ fontSize: '0.85em', color: '#999', margin: '0 0 0.5rem' }}>
        Nexo Tax Calculator
      </p>
      <a
        href="https://github.com/pexea12/nexo-tax"
        target="_blank"
        rel="noopener noreferrer"
        style={{ fontSize: '0.85em', color: '#646cff' }}
      >
        View on GitHub
      </a>
    </footer>
  )
}

interface ResultsViewProps {
  output: string
  isLoading?: boolean
}

export default function ResultsView({ output, isLoading }: ResultsViewProps) {
  return (
    <div style={{ marginTop: '2rem' }}>
      {isLoading && (
        <div style={{ marginBottom: '1rem', color: '#ffd700' }}>
          Calculating... Please wait...
        </div>
      )}
      {output && (
        <div>
          <h3>Tax Summary</h3>
          <pre
            style={{
              maxHeight: '600px',
              overflowY: 'auto',
              textAlign: 'left',
              whiteSpace: 'pre-wrap',
              wordWrap: 'break-word',
            }}
          >
            {output}
          </pre>
        </div>
      )}
    </div>
  )
}

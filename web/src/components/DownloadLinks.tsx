interface DownloadLinksProps {
  files: Record<string, string>
  disabled?: boolean
}

export default function DownloadLinks({ files, disabled }: DownloadLinksProps) {
  if (Object.keys(files).length === 0) {
    return null
  }

  const handleDownload = (filename: string, content: string) => {
    const blob = new Blob([content], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ marginTop: '2rem' }}>
      <h3>Download Audit Files</h3>
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        {Object.entries(files).map(([filename, content]) => (
          <button
            key={filename}
            onClick={() => handleDownload(filename, content)}
            disabled={disabled}
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.9em',
            }}
          >
            📥 {filename}
          </button>
        ))}
      </div>
    </div>
  )
}

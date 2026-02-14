import React, { useState } from 'react'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
}

export default function FileUpload({ onFilesSelected, disabled }: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      setDragActive(e.type === 'dragenter' || e.type === 'dragover')
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (disabled) return

    const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.csv'))
    if (files.length > 0) {
      onFilesSelected(files)
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      onFilesSelected(files)
    }
  }

  return (
    <div
      style={{
        padding: '2rem',
        border: '2px dashed #646cff',
        borderRadius: '8px',
        backgroundColor: dragActive ? '#1a1a2e' : 'transparent',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
      }}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        type="file"
        multiple
        accept=".csv"
        onChange={handleFileInput}
        disabled={disabled}
        style={{ display: 'none' }}
        id="file-input"
      />
      <label
        htmlFor="file-input"
        style={{
          display: 'block',
          cursor: disabled ? 'not-allowed' : 'pointer',
        }}
      >
        <div style={{ fontSize: '1.2em', marginBottom: '0.5rem' }}>
          Drag and drop your Nexo CSV files here
        </div>
        <div style={{ fontSize: '0.9em', color: '#999' }}>or click to select files</div>
      </label>
    </div>
  )
}

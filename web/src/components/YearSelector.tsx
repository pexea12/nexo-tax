import { DetectedYears } from '../types'

interface YearSelectorProps {
  years: DetectedYears
  onYearsChange: (years: DetectedYears) => void
  disabled?: boolean
}

export default function YearSelector({ years, onYearsChange, disabled }: YearSelectorProps) {
  if (Object.keys(years).length === 0) {
    return <div>No years detected in CSV files</div>
  }

  const handleToggle = (year: number) => {
    onYearsChange({
      ...years,
      [year]: !years[year],
    })
  }

  const selectedYears = Object.entries(years)
    .filter(([_, selected]) => selected)
    .map(([year]) => year)
    .sort()

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <h3>Tax Years</h3>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        {Object.keys(years)
          .map(Number)
          .sort()
          .map((year) => (
            <label key={year} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={years[year]}
                onChange={() => handleToggle(year)}
                disabled={disabled}
              />
              {year}
            </label>
          ))}
      </div>
      {selectedYears.length === 0 && (
        <div style={{ color: '#ff6b6b', marginTop: '0.5rem' }}>
          Please select at least one year
        </div>
      )}
    </div>
  )
}

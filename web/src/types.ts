export interface CalculationResult {
  console: string
  audit_files: Record<string, string>
}

export interface DetectedYears {
  [key: number]: boolean
}

declare global {
  interface Window {
    plausible?: (event: string, options?: { props?: Record<string, string | number> }) => void
  }
}

export function trackEvent(name: string, props?: Record<string, string | number>) {
  window.plausible?.(name, props ? { props } : undefined)
}

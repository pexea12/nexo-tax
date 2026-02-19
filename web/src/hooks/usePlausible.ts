import { track } from '@plausible-analytics/tracker'

export function trackEvent(name: string, props?: Record<string, string | number>) {
  track(name, props ? { props } : undefined)
}

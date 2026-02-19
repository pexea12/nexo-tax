import { track } from '@plausible-analytics/tracker'

export function trackEvent(name: string, props?: Record<string, string>) {
  track(name, props ? { props } : {})
}

import { init } from '@plausible-analytics/tracker'
import * as Sentry from '@sentry/react'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

init({ domain: 'nexo.archiesee.com' })

Sentry.init({
  dsn: 'https://5325eebe94e0f41be1b7a648819cb96f@o200755.ingest.us.sentry.io/4510896434642944',
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

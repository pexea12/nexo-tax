import React, { useState } from 'react'

type SubmitState = 'idle' | 'submitting' | 'success' | 'error'

const ACCESS_KEY = '45517816-0505-4b26-a2a8-1081683b2225'
const ENDPOINT = 'https://api.web3forms.com/submit'

export default function FeedbackForm() {
  const [rating, setRating] = useState(0)
  const [hovered, setHovered] = useState(0)
  const [worked, setWorked] = useState('')
  const [improve, setImprove] = useState('')
  const [email, setEmail] = useState('')
  const [state, setState] = useState<SubmitState>('idle')
  const [errorMsg, setErrorMsg] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (rating === 0) return

    setState('submitting')
    try {
      const formData = new FormData()
      formData.append('access_key', ACCESS_KEY)
      formData.append('rating', String(rating))
      formData.append('worked', worked)
      formData.append('improve', improve)
      formData.append('email', email)

      const res = await fetch(ENDPOINT, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json().catch(() => ({}))
      if (data.success) {
        setState('success')
      } else {
        setErrorMsg(data?.message ?? 'Submission failed. Please try again.')
        setState('error')
      }
    } catch {
      setErrorMsg('Network error. Please try again.')
      setState('error')
    }
  }

  if (state === 'success') {
    return (
      <div style={containerStyle}>
        <p style={{ fontSize: '2rem', margin: '0 0 0.5rem' }}>🙏</p>
        <p style={{ margin: 0, fontWeight: 600 }}>Thanks for your feedback!</p>
        <p style={{ margin: '0.25rem 0 0', color: '#999', fontSize: '0.9em' }}>
          It helps improve the tool for everyone.
        </p>
      </div>
    )
  }

  const stars = [1, 2, 3, 4, 5]
  const active = hovered || rating

  return (
    <div style={containerStyle}>
      <h3 style={{ margin: '0 0 0.25rem', fontSize: '1.1em' }}>Share your feedback</h3>
      <p style={{ margin: '0 0 1.25rem', color: '#999', fontSize: '0.88em' }}>
        Help improve this tool — takes 30 seconds.
      </p>

      <form onSubmit={handleSubmit}>
        {/* Star rating */}
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={labelStyle}>How useful was this tool?</label>
          <div
            style={{ display: 'flex', gap: '0.4rem', marginTop: '0.5rem' }}
            onMouseLeave={() => setHovered(0)}
          >
            {stars.map((s) => (
              <button
                key={s}
                type="button"
                aria-label={`${s} star${s !== 1 ? 's' : ''}`}
                onClick={() => setRating(s)}
                onMouseEnter={() => setHovered(s)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '2rem',
                  padding: '0',
                  lineHeight: 1,
                  color: s <= active ? '#ffd700' : '#444',
                  transition: 'color 0.1s, transform 0.1s',
                  transform: s <= active ? 'scale(1.15)' : 'scale(1)',
                }}
              >
                ★
              </button>
            ))}
          </div>
          {rating > 0 && (
            <p style={{ margin: '0.4rem 0 0', fontSize: '0.82em', color: '#888' }}>
              {['', 'Not useful', 'Somewhat useful', 'Useful', 'Very useful', 'Extremely useful'][rating]}
            </p>
          )}
        </div>

        {/* What worked well */}
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="fb-worked" style={labelStyle}>What worked well? <span style={{ color: '#666' }}>(optional)</span></label>
          <textarea
            id="fb-worked"
            value={worked}
            onChange={(e) => setWorked(e.target.value)}
            placeholder="e.g. The disposals calculation was accurate..."
            rows={2}
            style={textareaStyle}
          />
        </div>

        {/* What could be improved */}
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="fb-improve" style={labelStyle}>What could be improved? <span style={{ color: '#666' }}>(optional)</span></label>
          <textarea
            id="fb-improve"
            value={improve}
            onChange={(e) => setImprove(e.target.value)}
            placeholder="e.g. The loading time was slow..."
            rows={2}
            style={textareaStyle}
          />
        </div>

        {/* Email */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label htmlFor="fb-email" style={labelStyle}>Email <span style={{ color: '#666' }}>(optional — only if you'd like a reply)</span></label>
          <input
            id="fb-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            style={{ ...textareaStyle, resize: 'none', height: 'auto', padding: '0.5rem 0.75rem' }}
          />
        </div>

        {state === 'error' && (
          <p style={{ color: '#f44336', fontSize: '0.88em', margin: '0 0 1rem' }}>{errorMsg}</p>
        )}

        <button
          type="submit"
          disabled={rating === 0 || state === 'submitting'}
          style={{
            padding: '0.6rem 1.75rem',
            fontWeight: 600,
            fontSize: '0.95em',
            opacity: rating === 0 ? 0.45 : 1,
            cursor: rating === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          {state === 'submitting' ? 'Sending…' : 'Send feedback'}
        </button>
      </form>
    </div>
  )
}

const containerStyle: React.CSSProperties = {
  marginTop: '2.5rem',
  padding: '1.5rem',
  background: '#161616',
  border: '1px solid #2a2a2a',
  borderRadius: '10px',
  textAlign: 'left',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '0.9em',
  marginBottom: '0.35rem',
  color: '#ccc',
}

const textareaStyle: React.CSSProperties = {
  width: '100%',
  background: '#1e1e1e',
  border: '1px solid #333',
  borderRadius: '6px',
  color: '#eee',
  padding: '0.5rem 0.75rem',
  fontSize: '0.9em',
  resize: 'vertical',
  boxSizing: 'border-box',
}

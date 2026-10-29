import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

function App() {
  const [file, setFile] = useState(null)
  const [capabilities, setCapabilities] = useState(null)
  const [target, setTarget] = useState('')
  const [ocrEnabled, setOcrEnabled] = useState(true)
  const [ocrLanguage, setOcrLanguage] = useState('eng')
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const polling = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/capabilities`)
      .then((response) => {
        if (!response.ok) throw new Error('Could not load capabilities')
        return response.json()
      })
      .then((data) => {
        setCapabilities(data)
        setOcrLanguage(data.ocr_languages?.[0] || 'eng')
      })
      .catch((reason) => setError(reason.message))
  }, [])

  useEffect(() => () => clearInterval(polling.current), [])

  const fileKind = file?.name.match(/\.pdf$/i)
    ? 'pdf'
    : file?.name.match(/\.docx$/i)
      ? 'docx'
    : file?.name.match(/\.xlsx$/i)
      ? 'xlsx'
    : file?.name.match(/\.pptx$/i)
      ? 'pptx'
    : file?.name.match(/\.(jpe?g|png|tiff?)$/i)
      ? 'image'
      : null
  const outputs = useMemo(() => capabilities?.supported_conversions?.filter(
    (conversion) => conversion.input === fileKind,
  ).map((conversion) => conversion.output) || [], [capabilities, fileKind])
  const selectedTarget = outputs.includes(target) ? target : (outputs[0] || '')

  function stopPolling() {
    clearInterval(polling.current)
    polling.current = null
  }

  async function pollJob(jobId) {
    stopPolling()
    polling.current = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`)
        const status = await response.json()
        if (!response.ok) throw new Error(status.detail?.message || 'Could not read job status')
        setJob(status)
        if (['completed', 'failed', 'cancelled', 'expired'].includes(status.status)) {
          stopPolling()
        }
      } catch (reason) {
        setError(reason.message)
        stopPolling()
      }
    }, 800)
  }

  async function submit(event) {
    event.preventEvent?.()
    event.preventDefault()
    if (!file || !selectedTarget) {
      setError('Choose a supported file and output format.')
      return
    }

    setSubmitting(true)
    setError('')
    setJob(null)
    const form = new FormData()
    form.append('file', file)
    form.append('target_format', selectedTarget)
    form.append('ocr_enabled', String(ocrEnabled))
    form.append('ocr_language', ocrLanguage)

    try {
      const response = await fetch(`${API_BASE}/api/v1/jobs`, {
        method: 'POST',
        body: form,
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail?.message || 'Upload failed')
      setJob({
        job_id: result.job_id,
        status: result.status,
        progress: 0,
        message: 'Waiting to be processed',
      })
      pollJob(result.job_id)
    } catch (reason) {
      setError(reason.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function download() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/jobs/${job.job_id}/download`)
      if (!response.ok) {
        const result = await response.json()
        throw new Error(result.detail?.message || 'Download failed')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${file.name.replace(/\.[^.]+$/, '')}.${selectedTarget}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setError(reason.message)
    }
  }

  async function cancel() {
    if (!job?.job_id) return
    await fetch(`${API_BASE}/api/v1/jobs/${job.job_id}`, { method: 'DELETE' })
    stopPolling()
    setJob((current) => current ? { ...current, status: 'cancelled', message: 'Job cancelled' } : current)
  }

  return (
    <main className="app-shell">
      <header>
        <div className="brand-mark">O</div>
        <div>
          <h1>OpenConvert</h1>
          <p>Private document conversion</p>
        </div>
      </header>

      <section className="converter-card">
        <form onSubmit={submit}>
          <label className={`drop-zone ${file ? 'has-file' : ''}`}>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf,.docx,.xlsx,.pptx"
              onChange={(event) => {
                setFile(event.target.files?.[0] || null)
                setError('')
              }}
            />
            <span className="drop-icon">{file ? '✓' : '+'}</span>
            <strong>{file ? file.name : 'Choose a document'}</strong>
            <small>{file ? `${Math.ceil(file.size / 1024)} KB` : 'JPG, PNG, TIFF, PDF, DOCX, XLSX, or PPTX'}</small>
          </label>

          <div className="options-grid">
            <label>
              Output format
              <select value={selectedTarget} onChange={(event) => setTarget(event.target.value)} disabled={!outputs.length}>
                {outputs.map((format) => <option key={format} value={format}>{format.toUpperCase()}</option>)}
              </select>
            </label>

            <label>
              OCR language
              <select value={ocrLanguage} onChange={(event) => setOcrLanguage(event.target.value)}>
                {(capabilities?.ocr_languages || ['eng']).map((language) =>
                  <option key={language} value={language}>{language.toUpperCase()}</option>
                )}
              </select>
            </label>
          </div>

          <label className="toggle">
            <input type="checkbox" checked={ocrEnabled} onChange={(event) => setOcrEnabled(event.target.checked)} />
            <span>Enable OCR</span>
          </label>

          <button className="primary-button" type="submit" disabled={!file || !selectedTarget || submitting}>
            {submitting ? 'Starting conversion...' : 'Convert document'}
          </button>
        </form>

        {error && <div className="alert" role="alert">{error}</div>}

        {job && (
          <div className="job-panel">
            <div className="job-heading">
              <div>
                <span className={`status status-${job.status}`}>{job.status}</span>
                <strong>{job.message}</strong>
              </div>
              {job.status === 'queued' || job.status === 'processing'
                ? <button type="button" className="text-button" onClick={cancel}>Cancel</button>
                : null}
            </div>
            <div className="progress-track">
              <div style={{ width: `${job.progress || 0}%` }} />
            </div>
            {job.status === 'completed' && (
              <button type="button" className="download-button" onClick={download}>
                Download {job.output_format?.toUpperCase()}
              </button>
            )}
            {job.status === 'failed' && <p className="job-error">Error: {job.error_code || 'processing_failed'}</p>}
            {job.status === 'expired' && <p className="job-error">This result has expired and is no longer available.</p>}
          </div>
        )}
        <p className="privacy-notice">
          Files are processed privately and deleted automatically after the retention window.
        </p>
      </section>
    </main>
  )
}

export default App

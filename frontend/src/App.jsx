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
  const [dragging, setDragging] = useState(false)
  const [theme, setTheme] = useState(() => localStorage.getItem('openconvert-theme') || 'dark')
  const [previewUrl, setPreviewUrl] = useState('')
  const polling = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('openconvert-theme', theme)
  }, [theme])

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

  useEffect(() => () => {
    clearInterval(polling.current)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  const fileKind = useMemo(() => {
    const name = file?.name || ''
    if (/\.pdf$/i.test(name)) return 'pdf'
    if (/\.docx$/i.test(name)) return 'docx'
    if (/\.xlsx$/i.test(name)) return 'xlsx'
    if (/\.pptx$/i.test(name)) return 'pptx'
    if (/\.(jpe?g|png|tiff?)$/i.test(name)) return 'image'
    return null
  }, [file])

  const outputs = useMemo(() => capabilities?.supported_conversions?.filter(
    (conversion) => conversion.input === fileKind,
  ).map((conversion) => conversion.output) || [], [capabilities, fileKind])
  const selectedTarget = outputs.includes(target) ? target : (outputs[0] || '')
  const supportsPreview = file && /^image\/(jpeg|png)/.test(file.type)

  function chooseFile(selected) {
    if (!selected) return
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(/^image\/(jpeg|png)/.test(selected.type) ? URL.createObjectURL(selected) : '')
    setFile(selected)
    setError('')
    setJob(null)
  }

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
        if (['completed', 'failed', 'cancelled', 'expired'].includes(status.status)) stopPolling()
      } catch (reason) {
        setError(reason.message)
        stopPolling()
      }
    }, 800)
  }

  async function submit(event) {
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
      const response = await fetch(`${API_BASE}/api/v1/jobs`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail?.message || 'Upload failed')
      const currentJob = { job_id: result.job_id, status: result.status, progress: 0, message: 'Waiting to be processed' }
      setJob(currentJob)
      pollJob(result.job_id)
    } catch (reason) {
      setError(reason.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function download() {
    const activeJob = job
    if (!activeJob?.job_id) return
    try {
      const response = await fetch(`${API_BASE}/api/v1/jobs/${activeJob.job_id}/download`)
      if (!response.ok) throw new Error('This result is no longer available')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${(file?.name || 'converted').replace(/\.[^.]+$/, '')}.${activeJob.output_format || selectedTarget}`
      link.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setError(reason.message)
    }
  }

  async function deleteJob(jobId) {
    await fetch(`${API_BASE}/api/v1/jobs/${jobId}`, { method: 'DELETE' }).catch(() => {})
    if (job?.job_id === jobId) {
      stopPolling()
      setJob((current) => current ? { ...current, status: 'cancelled', message: 'Deleted now' } : current)
    }
  }

  return (
    <main className="app-shell">
      <header>
        <div className="brand-mark">O</div>
        <div className="header-copy">
          <h1>OpenConvert</h1>
          <p>Private document conversion</p>
        </div>
        <button className="theme-button" type="button" aria-label="Toggle color theme"
          onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')}>
          {theme === 'light' ? '☾' : '☀'}
        </button>
      </header>

      <div className="workspace-grid">
        <section className="converter-card">
          <form onSubmit={submit}>
            <label
              className={`drop-zone ${file ? 'has-file' : ''} ${dragging ? 'dragging' : ''}`}
              onDragEnter={(event) => { event.preventEvent?.(); event.preventDefault(); setDragging(true) }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                chooseFile(event.dataTransfer.files?.[0])
              }}
            >
              <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf,.docx,.xlsx,.pptx"
                onChange={(event) => chooseFile(event.target.files?.[0])} />
              {supportsPreview && previewUrl ? (
                <img className="file-preview" src={previewUrl} alt="Selected file preview" />
              ) : (
                <span className="drop-icon">{file ? '✓' : '+'}</span>
              )}
              <strong>{file ? file.name : 'Choose or drop a document'}</strong>
              <small>{file ? `${Math.ceil(file.size / 1024)} KB · ${fileKind?.toUpperCase()}` : 'JPG, PNG, TIFF, PDF, DOCX, XLSX, or PPTX'}</small>
            </label>

            <div className="options-grid">
              <label>Output format
                <select value={selectedTarget} onChange={(event) => setTarget(event.target.value)} disabled={!outputs.length}>
                  {outputs.map((format) => <option key={format} value={format}>{format.toUpperCase()}</option>)}
                </select>
              </label>
              <label>OCR language
                <select value={ocrLanguage} onChange={(event) => setOcrLanguage(event.target.value)}>
                  {(capabilities?.ocr_languages || ['eng']).map((language) =>
                    <option key={language} value={language}>{language.toUpperCase()}</option>)}
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
                <div><span className={`status status-${job.status}`}>{job.status}</span><strong>{job.message}</strong></div>
                {(job.status === 'queued' || job.status === 'processing') &&
                  <button type="button" className="text-button" onClick={() => deleteJob(job.job_id)}>Delete now</button>}
              </div>
              <div className="progress-track"><div style={{ width: `${job.progress || 0}%` }} /></div>
              {job.status === 'completed' && <button type="button" className="download-button" onClick={() => download()}>{`Download ${job.output_format?.toUpperCase()}`}</button>}
              {job.status === 'failed' && <p className="job-error">Error: {job.error_code || 'processing_failed'}</p>}
              {job.status === 'cancelled' && <p className="job-error">This job was deleted and cleaned up.</p>}
            </div>
          )}
          <p className="privacy-notice">Files are processed privately and deleted automatically after the retention window.</p>
        </section>

      </div>
    </main>
  )
}

export default App

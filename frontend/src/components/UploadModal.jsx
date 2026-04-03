import { useState, useRef, useEffect } from 'react'
import { uploadDocument, listDocuments, deleteDocument, getUploadStatus } from '../services/api'

export default function UploadModal({ onClose, onUploaded, onDocCountChange }) {
  const [tab, setTab] = useState('upload')
  const [file, setFile] = useState(null)
  const [docs, setDocs] = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [status, setStatus] = useState(null) // { type: 'success'|'error', message }
  const [loading, setLoading] = useState(false)
  const [deletingFile, setDeletingFile] = useState(null)
  const inputRef = useRef()

  const fetchDocs = async () => {
    setDocsLoading(true)
    try {
      const data = await listDocuments()
      setDocs(data)
    } catch {
      setDocs([])
    } finally {
      setDocsLoading(false)
    }
  }

  useEffect(() => {
    fetchDocs()
  }, [])

  const handleDelete = async (filename) => {
    if (!confirm(`Remove "${filename}" from your knowledge base?`)) return
    setDeletingFile(filename)
    try {
      await deleteDocument(encodeURIComponent(filename))
      await fetchDocs()
      setStatus({ type: 'success', message: `✓ Removed "${filename}" from index` })
      // Refresh doc count in parent without closing modal
      try {
        const s = await getUploadStatus()
        onDocCountChange?.(s.indexed_chunks)
      } catch {}
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    } finally {
      setDeletingFile(null)
    }
  }

  const handleFile = (f) => {
    if (!f) return
    if (!['application/pdf', 'text/plain'].includes(f.type)) {
      setStatus({ type: 'error', message: 'Only PDF and .txt files are supported.' })
      return
    }
    setFile(f)
    setStatus(null)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    handleFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setStatus(null)
    try {
      const result = await uploadDocument(file)
      setStatus({ type: 'success', message: result.message })
      onUploaded?.(result)
      setFile(null)
      fetchDocs()
      // Switch to docs tab to show the newly indexed file
      setTimeout(() => setTab('docs'), 800)
    } catch (err) {
      setStatus({ type: 'error', message: err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="upload-modal">
        {/* Header */}
        <div className="upload-modal-header">
          <div className="upload-modal-title">
            <span className="upload-modal-icon">📚</span>
            Knowledge Base
          </div>
          <button className="upload-modal-close" onClick={onClose} title="Close">✕</button>
        </div>

        {/* Tabs */}
        <div className="upload-tabs">
          <button
            className={`upload-tab ${tab === 'upload' ? 'active' : ''}`}
            onClick={() => { setTab('upload'); setStatus(null) }}
          >
            ⬆ Upload File
          </button>
          <button
            className={`upload-tab ${tab === 'docs' ? 'active' : ''}`}
            onClick={() => { setTab('docs'); setStatus(null); fetchDocs() }}
          >
            🗂 My Documents
            {docs.length > 0 && <span className="tab-badge">{docs.length}</span>}
          </button>
        </div>

        {/* Upload Tab */}
        {tab === 'upload' && (
          <div className="upload-tab-content">
            <p className="upload-description">
              Upload a PDF or text file to use as context in your chats.
            </p>

            <div
              className="drop-zone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => inputRef.current.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.txt,text/plain,application/pdf"
                className="upload-file-input"
                onChange={(e) => handleFile(e.target.files[0])}
              />
              {file ? (
                <div>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>📄</div>
                  <strong style={{ color: 'var(--text)' }}>{file.name}</strong>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-dim)' }}>
                    {(file.size / 1024).toFixed(1)} KB · Ready to index
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: 32, marginBottom: 10, opacity: 0.35 }}>⬆</div>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>Click or drag a file here</div>
                  <div style={{ fontSize: 11, opacity: 0.5 }}>PDF · TXT · max 10 MB</div>
                </div>
              )}
            </div>

            {status && (
              <div className={`upload-status ${status.type}`}>
                {status.message}
              </div>
            )}

            <div className="modal-actions">
              <button className="btn-ghost" onClick={onClose}>Cancel</button>
              <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={!file || loading}
              >
                {loading ? (
                  <span className="btn-loading"><span className="spinner" />Indexing…</span>
                ) : 'Upload & Index'}
              </button>
            </div>
          </div>
        )}

        {/* My Documents Tab */}
        {tab === 'docs' && (
          <div className="upload-tab-content">
            {status && (
              <div className={`upload-status ${status.type}`} style={{ marginBottom: 16 }}>
                {status.message}
              </div>
            )}

            {docsLoading ? (
              <div className="docs-empty-state">
                <div className="docs-spinner" />
                <span>Loading documents…</span>
              </div>
            ) : docs.length === 0 ? (
              <div className="docs-empty-state">
                <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.2 }}>📭</div>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>No documents indexed yet</div>
                <div style={{ fontSize: 12, opacity: 0.5 }}>
                  Upload a PDF or text file to get started
                </div>
                <button
                  className="btn-primary"
                  style={{ marginTop: 16 }}
                  onClick={() => setTab('upload')}
                >
                  Upload a File
                </button>
              </div>
            ) : (
              <>
                <div className="docs-list-header">
                  <span className="doc-list-title">{docs.length} indexed file{docs.length !== 1 ? 's' : ''}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {docs.reduce((sum, d) => sum + d.chunks, 0)} total chunks
                  </span>
                </div>
                <div className="doc-list">
                  {docs.map((doc) => (
                    <div
                      className={`doc-item ${deletingFile === doc.filename ? 'deleting' : ''}`}
                      key={doc.filename}
                    >
                      <div className="doc-item-icon">📄</div>
                      <div className="doc-info">
                        <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                        <span className="doc-chunks">{doc.chunks} chunks</span>
                      </div>
                      <button
                        className="doc-delete-btn"
                        onClick={() => handleDelete(doc.filename)}
                        disabled={deletingFile === doc.filename}
                        title="Remove from knowledge base"
                      >
                        {deletingFile === doc.filename ? '…' : '🗑'}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="modal-actions" style={{ marginTop: 20 }}>
              <button className="btn-ghost" onClick={onClose}>Close</button>
              <button className="btn-ghost" onClick={() => setTab('upload')}>+ Upload More</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

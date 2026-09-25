'use client'

import { useState, useEffect, useRef } from 'react'

interface DocumentItem {
  doc_id: string
  title: string
  doc_type: string
  chunk_count: number
  source?: string
  created_at?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function FileUpload() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [docType, setDocType] = useState('report')
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/items`)
      if (res.ok) {
        const data = await res.json()
        setDocuments(data.documents || [])
      }
    } catch {
      // Ignore network errors on init
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const file = files[0]

    setIsUploading(true)
    setStatusMessage(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_type', docType)

    try {
      const res = await fetch(`${API_BASE}/api/documents/upload?doc_type=${encodeURIComponent(docType)}`, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (res.ok) {
        setStatusMessage({
          type: 'success',
          text: `🎉 ${data.message || `Indexed ${file.name} successfully into Qdrant & pgvector!`}`,
        })
        fetchDocuments()
      } else {
        setStatusMessage({
          type: 'error',
          text: data.detail || 'Upload failed. Please ensure file is valid text.',
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setStatusMessage({
        type: 'error',
        text: `Network error uploading document: ${msg}`,
      })
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
          Knowledge Base & Document Ingestion
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Upload reports, policies, or market data to feed both Qdrant Vector DB & PostgreSQL pgvector HNSW index.
        </p>
      </div>

      {/* Upload Box */}
      <div
        className="rounded-2xl p-6 border transition-all"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Document Category:
            </label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border outline-none cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-raised)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="report">📊 Market & Financial Report</option>
              <option value="policy">📜 Corporate Policy & Guidelines</option>
              <option value="product_doc">📦 Product & Tech Specifications</option>
            </select>
          </div>

          <div className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Dual Indexing: Qdrant + pgvector Active
          </div>
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragActive(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all"
          style={{
            borderColor: dragActive ? 'var(--accent-blue)' : 'var(--border)',
            backgroundColor: dragActive ? 'rgba(59, 130, 246, 0.05)' : 'var(--bg-base)',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf,.csv,.md,.json"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-3 bg-blue-500/10 text-blue-400 text-2xl">
            {isUploading ? '⏳' : '📁'}
          </div>

          <h3 className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            {isUploading ? 'Chunking & Embedding Document...' : 'Click to select or drag and drop document'}
          </h3>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Supports UTF-8 / Text files (.txt, .md, .csv, .json) • Embedded with nomic-embed-text-v1
          </p>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div
            className={`mt-4 p-3.5 rounded-xl text-xs font-medium border flex items-center gap-2 ${
              statusMessage.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            <span>{statusMessage.type === 'success' ? '✅' : '⚠️'}</span>
            <span>{statusMessage.text}</span>
          </div>
        )}
      </div>

      {/* Ingested Documents List */}
      <div
        className="rounded-2xl border overflow-hidden"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Active Knowledge Repository
            </h3>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {documents.length} document sources ready for semantic hybrid search
            </p>
          </div>
          <button
            onClick={fetchDocuments}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border hover:bg-white/5 transition-all"
            style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}
          >
            ↻ Refresh
          </button>
        </div>

        <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
          {documents.length === 0 ? (
            <div className="p-8 text-center text-xs" style={{ color: 'var(--text-muted)' }}>
              No custom documents uploaded yet. Default system documents are loaded from seed.
            </div>
          ) : (
            documents.map((doc, idx) => (
              <div
                key={idx}
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-lg">📄</span>
                  <div>
                    <h4 className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {doc.title}
                    </h4>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      ID: {doc.doc_id} • {doc.source || 'Dual Indexed'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5">
                  <span
                    className="text-[11px] font-medium px-2.5 py-1 rounded-full capitalize"
                    style={{
                      backgroundColor: 'var(--bg-raised)',
                      color: 'var(--accent-blue)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {doc.doc_type}
                  </span>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    {doc.chunk_count} chunks
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

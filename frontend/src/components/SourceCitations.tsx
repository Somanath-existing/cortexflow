'use client'

interface Source {
  agent: string
  task: string
  type: 'database' | 'document'
}

export default function SourceCitations({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null

  return (
    <div
      className="mt-3 pt-3 border-t"
      style={{ borderColor: 'var(--border)' }}
    >
      <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
        Sources
      </p>
      <div className="space-y-1">
        {sources.map((source, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span>{source.type === 'database' ? '🗄️' : '📄'}</span>
            <span style={{ color: 'var(--text-muted)' }}>{source.task}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

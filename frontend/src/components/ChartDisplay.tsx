'use client'

import { useEffect, useRef } from 'react'

interface ChartDisplayProps {
  chartJson: string | null
}

export default function ChartDisplay({ chartJson }: ChartDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartJson || !containerRef.current) return

    let parsed: unknown
    try {
      parsed = typeof chartJson === 'string' ? JSON.parse(chartJson) : chartJson
    } catch {
      return
    }

    // Dynamically load Plotly to avoid SSR issues
    import('plotly.js').then((Plotly) => {
      if (!containerRef.current) return
      const { data, layout } = parsed as { data: unknown[]; layout: unknown }
      Plotly.newPlot(containerRef.current, data as Plotly.Data[], layout as Plotly.Layout, {
        responsive: true,
        displayModeBar: false,
      })
    }).catch(() => {
      // Plotly not available — show raw data message
      if (containerRef.current) {
        containerRef.current.innerHTML =
          '<p style="color:var(--text-muted);font-size:12px;">Chart data available but Plotly not loaded.</p>'
      }
    })

    return () => {
      if (containerRef.current) {
        import('plotly.js').then((Plotly) => {
          if (containerRef.current) Plotly.purge(containerRef.current)
        })
      }
    }
  }, [chartJson])

  if (!chartJson) return null

  return (
    <div
      className="mt-3 rounded-lg overflow-hidden"
      style={{ backgroundColor: 'var(--bg-base)' }}
    >
      <div ref={containerRef} style={{ width: '100%', minHeight: '300px' }} />
    </div>
  )
}

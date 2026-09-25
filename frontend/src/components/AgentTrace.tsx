'use client'

export interface Step {
  type: string
  node?: string
  message?: string
  data?: {
    plan?: string[]
    current_step?: number
    tool_results_count?: number
  }
}

const NODE_META: Record<string, { emoji: string; color: string; label: string }> = {
  planner:    { emoji: '📋', color: 'border-purple-500',  label: 'Planner' },
  researcher: { emoji: '🔍', color: 'border-blue-500',   label: 'Researcher' },
  sql_agent:  { emoji: '🗄️', color: 'border-green-500',  label: 'SQL Agent' },
  critic:     { emoji: '🧐', color: 'border-yellow-500', label: 'Critic' },
  responder:  { emoji: '✍️', color: 'border-emerald-500',label: 'Responder' },
  status:     { emoji: '⚡', color: 'border-gray-600',   label: 'System' },
}

export default function AgentTrace({
  steps,
  isLive,
}: {
  steps: Step[]
  isLive: boolean
}) {
  return (
    <div className="space-y-2">
      {steps.map((step, i) => {
        const meta = NODE_META[step.node ?? 'status'] ?? NODE_META.status
        const isLatest = isLive && i === steps.length - 1

        return (
          <div
            key={i}
            className={`rounded-lg p-3 border-l-2 ${meta.color} text-sm`}
            style={{ backgroundColor: 'var(--bg-raised)' }}
          >
            <div className="flex items-center gap-2 font-medium" style={{ color: 'var(--text-primary)' }}>
              <span>{meta.emoji}</span>
              <span>{meta.label}</span>
              {isLatest && (
                <span className="ml-auto animate-pulse" style={{ color: 'var(--accent-blue)' }}>
                  ●
                </span>
              )}
            </div>

            {step.message && (
              <p className="mt-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                {step.message}
              </p>
            )}

            {step.data?.plan && step.data.plan.length > 0 && (
              <div className="mt-2 space-y-1">
                {step.data.plan.map((p: string, j: number) => (
                  <div
                    key={j}
                    className="text-xs flex gap-1"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <span className="shrink-0 opacity-50">{j + 1}.</span>
                    <span>{p}</span>
                  </div>
                ))}
              </div>
            )}

            {step.data?.tool_results_count !== undefined &&
              step.data.tool_results_count > 0 && (
                <p className="mt-1 text-xs" style={{ color: 'var(--accent-green)' }}>
                  {step.data.tool_results_count} result{step.data.tool_results_count !== 1 ? 's' : ''} collected
                </p>
              )}
          </div>
        )
      })}
    </div>
  )
}

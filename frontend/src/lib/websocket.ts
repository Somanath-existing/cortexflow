export type WSMessage =
  | { type: 'status'; message: string }
  | { type: 'agent_step'; node: string; data: AgentStepData }
  | { type: 'final_answer'; answer: string; sources: Source[]; chart_data: unknown }
  | { type: 'error'; message: string }

export interface AgentStepData {
  plan?: string[]
  current_step?: number
  tool_results_count?: number
}

export interface Source {
  agent: string
  task: string
  type: 'database' | 'document'
}

export function createWebSocket(sessionId: string): WebSocket {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000'
  return new WebSocket(`${wsUrl}/api/chat/ws/${sessionId}`)
}

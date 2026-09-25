const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function fetchAnalytics() {
  const res = await fetch(`${API_URL}/api/analytics/regional-summary`)
  if (!res.ok) throw new Error('Failed to fetch analytics')
  return res.json()
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`)
    return res.ok
  } catch {
    return false
  }
}

'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

interface RegionalItem {
  state: string
  quarter: string
  year: number
  product_category: string
  total_revenue: number
  total_units: number
}

interface ChurnCustomer {
  company_name: string
  region: string
  city: string
  health_score: number
  churn_risk: string
  last_order_days_ago: number
  revenue_trend: string
}

interface TopCustomer {
  customer_id: string
  company_name: string
  region: string
  order_count: number
  total_revenue: number
}

interface HeadToHeadItem {
  state: string
  quarter: string
  year: number
  total_revenue: number
  total_units: number
}

interface DashboardProps {
  onAskAI?: (prompt: string) => void
}

export default function Dashboard({ onAskAI }: DashboardProps) {
  const [regionalData, setRegionalData] = useState<RegionalItem[]>([])
  const [churnData, setChurnData] = useState<ChurnCustomer[]>([])
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([])
  const [headToHead, setHeadToHead] = useState<HeadToHeadItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchAllData = async () => {
    setLoading(true)
    try {
      const [regRes, churnRes, topRes, h2hRes] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/regional-summary`).then((r) => r.json()).catch(() => ({ data: [] })),
        fetch(`${API_BASE}/api/analytics/churn-risk`).then((r) => r.json()).catch(() => ({ data: [] })),
        fetch(`${API_BASE}/api/analytics/top-customers`).then((r) => r.json()).catch(() => ({ data: [] })),
        fetch(`${API_BASE}/api/analytics/kerala-vs-karnataka`).then((r) => r.json()).catch(() => ({ data: [] })),
      ])

      setRegionalData(regRes.data || [])
      setChurnData(churnRes.data || [])
      setTopCustomers(topRes.data || [])
      setHeadToHead(h2hRes.data || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAllData()
  }, [])

  // KPI Calculations
  const totalRevenue = regionalData.reduce((acc, curr) => acc + (Number(curr.total_revenue) || 0), 0)
  const highRiskCount = churnData.filter((c) => c.churn_risk === 'HIGH').length
  const topCustomer = topCustomers[0] || null

  // Category breakdown
  const categoryTotals: Record<string, number> = {}
  regionalData.forEach((item) => {
    const cat = item.product_category || 'Other'
    categoryTotals[cat] = (categoryTotals[cat] || 0) + (Number(item.total_revenue) || 0)
  })

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(val)
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-8 animate-fadeIn">
      {/* Dashboard Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Executive KPI & Market Intelligence
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Real-time telemetry aggregated from PostgreSQL Northwind schema & predictive churn analytics.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchAllData}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold rounded-xl border transition-all hover:bg-white/5 flex items-center gap-2"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
          >
            <span>{loading ? '⏳' : '↻'}</span>
            <span>Refresh Analytics</span>
          </button>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 */}
        <div
          className="p-5 rounded-2xl border transition-all"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Total Regional Revenue
            </span>
            <span className="text-lg">💰</span>
          </div>
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {formatCurrency(totalRevenue)}
          </div>
          <p className="text-[11px] mt-1 text-emerald-400 font-medium">
            Across Kerala & Karnataka territories
          </p>
        </div>

        {/* Card 2 */}
        <div
          className="p-5 rounded-2xl border transition-all"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              High Churn Risk
            </span>
            <span className="text-lg">🛡️</span>
          </div>
          <div className="text-2xl font-bold text-red-400">
            {highRiskCount} Accounts
          </div>
          <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
            Health score below 55.0 threshold
          </p>
        </div>

        {/* Card 3 */}
        <div
          className="p-5 rounded-2xl border transition-all"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Top Client Account
            </span>
            <span className="text-lg">👑</span>
          </div>
          <div className="text-lg font-bold truncate" style={{ color: 'var(--text-primary)' }}>
            {topCustomer?.company_name || 'Loading...'}
          </div>
          <p className="text-[11px] mt-1 text-purple-400 font-medium">
            {topCustomer ? `${formatCurrency(topCustomer.total_revenue)} • ${topCustomer.region}` : ''}
          </p>
        </div>

        {/* Card 4 */}
        <div
          className="p-5 rounded-2xl border transition-all"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Active Vector Store
            </span>
            <span className="text-lg">⚡</span>
          </div>
          <div className="text-lg font-bold text-blue-400">
            pgvector + Qdrant
          </div>
          <p className="text-[11px] mt-1 text-emerald-400 font-medium">
            Dual hybrid search enabled
          </p>
        </div>
      </div>

      {/* Grid: Kerala vs Karnataka & Product Categories */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Head-to-Head Comparison */}
        <div
          className="p-6 rounded-2xl border space-y-4"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              ⚔️ Kerala vs Karnataka Performance
            </h3>
            {onAskAI && (
              <button
                onClick={() => onAskAI('Compare Kerala vs Karnataka revenue and trends for 2024 with a chart')}
                className="text-xs text-blue-400 hover:underline"
              >
                Analyze with Agent →
              </button>
            )}
          </div>

          <div className="space-y-3">
            {headToHead.slice(0, 6).map((item, idx) => {
              const maxRev = 1500000
              const pct = Math.min(100, Math.round((Number(item.total_revenue) / maxRev) * 100))
              const isKerala = item.state === 'Kerala'
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span style={{ color: isKerala ? '#38bdf8' : '#a855f7' }}>
                      {item.state} • {item.quarter} {item.year}
                    </span>
                    <span style={{ color: 'var(--text-primary)' }}>
                      {formatCurrency(Number(item.total_revenue))} ({item.total_units} units)
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--bg-raised)' }}>
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${pct}%`,
                        background: isKerala
                          ? 'linear-gradient(90deg, #0284c7, #38bdf8)'
                          : 'linear-gradient(90deg, #7e22ce, #c084fc)',
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Product Category Breakdown */}
        <div
          className="p-6 rounded-2xl border space-y-4"
          style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              📊 Product Revenue Distribution
            </h3>
            {onAskAI && (
              <button
                onClick={() => onAskAI('Generate a pie chart showing product category revenue distribution')}
                className="text-xs text-blue-400 hover:underline"
              >
                Generate Pie Chart →
              </button>
            )}
          </div>

          <div className="space-y-4 pt-2">
            {Object.entries(categoryTotals).map(([cat, rev], idx) => {
              const total = totalRevenue || 1
              const pct = Math.round((rev / total) * 100)
              const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ec4899']
              const color = colors[idx % colors.length]

              return (
                <div key={cat} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span style={{ color: 'var(--text-primary)' }}>{cat}</span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {formatCurrency(rev)} ({pct}%)
                    </span>
                  </div>
                  <div className="w-full h-2.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--bg-raised)' }}>
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Customer Health & Churn Risk Radar */}
      <div
        className="rounded-2xl border overflow-hidden"
        style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <div className="p-5 border-b flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
              🩺 Customer Retention & Churn Risk Table
            </h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Real-time customer health scores calculated from recency, frequency, and order trends.
            </p>
          </div>
          {onAskAI && (
            <button
              onClick={() => onAskAI('Which customers in Kerala have the highest churn risk and what are our retention actions?')}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-all"
            >
              Analyze Churn with CortexFlow →
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead style={{ backgroundColor: 'var(--bg-raised)', color: 'var(--text-muted)' }}>
              <tr>
                <th className="py-3 px-4 font-semibold">Company</th>
                <th className="py-3 px-4 font-semibold">Territory</th>
                <th className="py-3 px-4 font-semibold">Health Score</th>
                <th className="py-3 px-4 font-semibold">Churn Risk</th>
                <th className="py-3 px-4 font-semibold">Revenue Trend</th>
                <th className="py-3 px-4 font-semibold">Last Order</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: 'var(--border)' }}>
              {churnData.map((c, i) => {
                const scoreColor =
                  c.health_score >= 75 ? '#10b981' : c.health_score >= 55 ? '#f59e0b' : '#ef4444'
                const isHighRisk = c.churn_risk === 'HIGH'

                return (
                  <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                      {c.company_name}
                    </td>
                    <td className="py-3 px-4" style={{ color: 'var(--text-muted)' }}>
                      {c.city}, {c.region}
                    </td>
                    <td className="py-3 px-4 font-bold" style={{ color: scoreColor }}>
                      {c.health_score} / 100
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          isHighRisk
                            ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        }`}
                      >
                        {c.churn_risk}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                      {c.revenue_trend}
                    </td>
                    <td className="py-3 px-4" style={{ color: 'var(--text-muted)' }}>
                      {c.last_order_days_ago} days ago
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

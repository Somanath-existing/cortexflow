'use client'

import { useState } from 'react'
import ChatInterface from '@/components/ChatInterface'
import Dashboard from '@/components/Dashboard'
import FileUpload from '@/components/FileUpload'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard' | 'documents'>('chat')
  const [chatQuery, setChatQuery] = useState('')

  const handleAskAI = (prompt: string) => {
    setChatQuery(prompt)
    setActiveTab('chat')
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* Top Universal App Navigation */}
      <header
        className="h-14 border-b px-6 flex items-center justify-between shrink-0 z-30"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20 font-black text-white text-base">
            C
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              CortexFlow
            </h1>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Enterprise Autonomous Intelligence
            </p>
          </div>
        </div>

        {/* Center Tabs */}
        <nav className="flex items-center p-1 rounded-xl border" style={{ backgroundColor: 'var(--bg-base)', borderColor: 'var(--border)' }}>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'chat'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                : 'hover:text-white'
            }`}
            style={{ color: activeTab === 'chat' ? '#ffffff' : 'var(--text-muted)' }}
          >
            <span>💬</span>
            <span>Autonomous Chat</span>
          </button>

          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'dashboard'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                : 'hover:text-white'
            }`}
            style={{ color: activeTab === 'dashboard' ? '#ffffff' : 'var(--text-muted)' }}
          >
            <span>📈</span>
            <span>Executive Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('documents')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'documents'
                ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm'
                : 'hover:text-white'
            }`}
            style={{ color: activeTab === 'documents' ? '#ffffff' : 'var(--text-muted)' }}
          >
            <span>📁</span>
            <span>Document Ingestion</span>
          </button>
        </nav>

        {/* Right Status */}
        <div className="flex items-center gap-2 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="hidden sm:inline" style={{ color: 'var(--text-muted)' }}>
            Cluster Active
          </span>
        </div>
      </header>

      {/* Main Tab Content */}
      <main className="flex-1 overflow-y-auto">
        {activeTab === 'chat' && <ChatInterface initialQuery={chatQuery} />}
        {activeTab === 'dashboard' && <Dashboard onAskAI={handleAskAI} />}
        {activeTab === 'documents' && <FileUpload />}
      </main>
    </div>
  )
}

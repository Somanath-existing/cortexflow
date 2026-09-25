import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CortexFlow — Enterprise Data Worker',
  description: 'MCP-Powered Autonomous Enterprise Data Intelligence. Ask questions about your business data and get AI-researched answers.',
  keywords: ['enterprise AI', 'business intelligence', 'data analytics', 'MCP', 'autonomous AI'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  )
}

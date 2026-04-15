import React from 'react'
import { Sidebar } from '@/components/Sidebar'

export function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col h-full relative transition-all duration-300">
        {children}
      </main>
    </div>
  )
}

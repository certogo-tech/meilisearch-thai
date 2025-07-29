"use client"

import * as React from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { AppHeader } from "@/components/app-header"
import { AppBreadcrumb } from "@/components/app-breadcrumb"
import { Sheet, SheetContent } from "@/components/ui/sheet"
import { useRealTimeNotifications } from "@/hooks/use-real-time-notifications"
import { cn } from "@/lib/utils"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false)
  
  // Initialize real-time notifications
  useRealTimeNotifications()

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex">
        <AppSidebar 
          isCollapsed={sidebarCollapsed} 
          onToggle={toggleSidebar} 
        />
      </aside>

      {/* Mobile Sidebar */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="p-0 w-64">
          <AppSidebar 
            isCollapsed={false} 
            onToggle={() => setMobileMenuOpen(false)} 
          />
        </SheetContent>
      </Sheet>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <AppHeader 
          onMenuToggle={toggleMobileMenu}
          showMenuButton={true}
        />

        {/* Breadcrumb */}
        <div className="border-b bg-background px-4 py-3">
          <AppBreadcrumb />
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <div className={cn(
            "h-full",
            // Add padding for content
            "p-6"
          )}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
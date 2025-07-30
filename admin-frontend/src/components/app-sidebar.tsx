"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { 
  LayoutDashboard, 
  BookOpen, 
  TestTube, 
  BarChart3, 
  Upload, 
  Settings, 
  Users,
  FileText,
  ChevronLeft,
  ChevronRight
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { Permission } from "@/types"

interface SidebarProps {
  isCollapsed: boolean
  onToggle: () => void
}

const navigationItems = [
  {
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    permissions: [Permission.VIEW_COMPOUNDS]
  },
  {
    title: "Compounds",
    href: "/admin/compounds",
    icon: BookOpen,
    permissions: [Permission.VIEW_COMPOUNDS]
  },
  {
    title: "Test Interface",
    href: "/admin/test",
    icon: TestTube,
    permissions: [Permission.VIEW_COMPOUNDS]
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
    permissions: [Permission.VIEW_ANALYTICS]
  },
  {
    title: "Import/Export",
    href: "/import-export",
    icon: Upload,
    permissions: [Permission.BULK_OPERATIONS]
  },
  {
    title: "Users",
    href: "/admin/users",
    icon: Users,
    permissions: [Permission.SYSTEM_ADMIN]
  },
  {
    title: "Audit Logs",
    href: "/admin/audit",
    icon: FileText,
    permissions: [Permission.SYSTEM_ADMIN]
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
    permissions: [Permission.VIEW_COMPOUNDS]
  }
]

export function AppSidebar({ isCollapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()
  const { hasPermission } = useAuth()

  const filteredItems = navigationItems.filter(item =>
    item.permissions.some(permission => hasPermission(permission))
  )

  return (
    <div className={cn(
      "relative flex h-full flex-col border-r bg-background transition-all duration-300",
      isCollapsed ? "w-16" : "w-64"
    )}>
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!isCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">TT</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold">Thai Tokenizer</span>
              <span className="text-xs text-muted-foreground">Admin Panel</span>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggle}
          className="h-8 w-8 p-0"
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
          <span className="sr-only">Toggle sidebar</span>
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {filteredItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link key={item.href} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start h-10",
                  isCollapsed ? "px-2" : "px-3",
                  isActive && "bg-secondary text-secondary-foreground"
                )}
              >
                <Icon className={cn("h-4 w-4", !isCollapsed && "mr-3")} />
                {!isCollapsed && (
                  <span className="truncate">{item.title}</span>
                )}
              </Button>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      {!isCollapsed && (
        <div className="border-t p-4">
          <div className="text-xs text-muted-foreground">
            <div>Version 1.0.0</div>
            <div className="mt-1">© 2024 Thai Tokenizer</div>
          </div>
        </div>
      )}
    </div>
  )
}
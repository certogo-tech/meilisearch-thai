"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Home } from "lucide-react"

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

interface BreadcrumbItem {
  title: string
  href?: string
}

const routeMap: Record<string, BreadcrumbItem[]> = {
  '/dashboard': [
    { title: 'Dashboard' }
  ],
  '/dictionary': [
    { title: 'Dictionary' }
  ],
  '/test': [
    { title: 'Test Interface' }
  ],
  '/analytics': [
    { title: 'Analytics' }
  ],
  '/import-export': [
    { title: 'Import/Export' }
  ],
  '/admin': [
    { title: 'Administration' }
  ],
  '/admin/users': [
    { title: 'Administration', href: '/admin' },
    { title: 'Users' }
  ],
  '/admin/audit': [
    { title: 'Administration', href: '/admin' },
    { title: 'Audit Logs' }
  ],
  '/settings': [
    { title: 'Settings' }
  ]
}

export function AppBreadcrumb() {
  const pathname = usePathname()
  
  // Don't show breadcrumbs on login page or root
  if (pathname === '/login' || pathname === '/') {
    return null
  }

  const breadcrumbItems = routeMap[pathname] || []

  if (breadcrumbItems.length === 0) {
    return null
  }

  return (
    <div className="flex items-center space-x-1 text-sm text-muted-foreground">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/dashboard" className="flex items-center">
                <Home className="h-4 w-4" />
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          
          {breadcrumbItems.map((item, index) => (
            <React.Fragment key={index}>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {item.href ? (
                  <BreadcrumbLink asChild>
                    <Link href={item.href}>{item.title}</Link>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage>{item.title}</BreadcrumbPage>
                )}
              </BreadcrumbItem>
            </React.Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  )
}
"use client"

import * as React from "react"
import { AlertCircle, CheckCircle, AlertTriangle, Info, X } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface SystemAlert {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  dismissible?: boolean
  persistent?: boolean
}

interface SystemAlertsProps {
  alerts: SystemAlert[]
  onDismiss?: (id: string) => void
}

const alertIcons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const alertVariants = {
  success: "border-green-200 bg-green-50 text-green-800 [&>svg]:text-green-600",
  error: "border-red-200 bg-red-50 text-red-800 [&>svg]:text-red-600",
  warning: "border-yellow-200 bg-yellow-50 text-yellow-800 [&>svg]:text-yellow-600",
  info: "border-blue-200 bg-blue-50 text-blue-800 [&>svg]:text-blue-600",
}

export function SystemAlerts({ alerts, onDismiss }: SystemAlertsProps) {
  const [dismissedAlerts, setDismissedAlerts] = React.useState<Set<string>>(new Set())

  const handleDismiss = (id: string) => {
    setDismissedAlerts(prev => new Set([...prev, id]))
    onDismiss?.(id)
  }

  const visibleAlerts = alerts.filter(alert => 
    !dismissedAlerts.has(alert.id) && !alert.persistent
  )

  if (visibleAlerts.length === 0) {
    return null
  }

  return (
    <div className="space-y-2">
      {visibleAlerts.map((alert) => {
        const Icon = alertIcons[alert.type]
        
        return (
          <Alert
            key={alert.id}
            className={cn(
              "relative",
              alertVariants[alert.type]
            )}
          >
            <Icon className="h-4 w-4" />
            <div className="flex-1">
              <AlertTitle className="mb-1">{alert.title}</AlertTitle>
              <AlertDescription>{alert.message}</AlertDescription>
            </div>
            {alert.dismissible !== false && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDismiss(alert.id)}
                className="absolute right-2 top-2 h-6 w-6 p-0 text-current hover:bg-current/10"
              >
                <X className="h-3 w-3" />
                <span className="sr-only">Dismiss alert</span>
              </Button>
            )}
          </Alert>
        )
      })}
    </div>
  )
}

// Hook for managing system alerts
export function useSystemAlerts() {
  const [alerts, setAlerts] = React.useState<SystemAlert[]>([
    {
      id: 'maintenance',
      type: 'warning',
      title: 'Scheduled Maintenance',
      message: 'System maintenance is scheduled for tonight at 2:00 AM UTC. Expected downtime: 30 minutes.',
      dismissible: true,
    },
    {
      id: 'performance',
      type: 'info',
      title: 'Performance Optimization',
      message: 'New caching layer has been deployed. You may notice improved response times.',
      dismissible: true,
    },
  ])

  const addAlert = React.useCallback((alert: Omit<SystemAlert, 'id'>) => {
    const newAlert: SystemAlert = {
      ...alert,
      id: Date.now().toString(),
    }
    setAlerts(prev => [newAlert, ...prev])
  }, [])

  const removeAlert = React.useCallback((id: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id))
  }, [])

  const clearAllAlerts = React.useCallback(() => {
    setAlerts([])
  }, [])

  return {
    alerts,
    addAlert,
    removeAlert,
    clearAllAlerts,
  }
}
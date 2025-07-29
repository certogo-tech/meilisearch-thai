"use client"

import * as React from "react"
import { 
  AlertTriangle, 
  CheckCircle, 
  Info, 
  XCircle,
  X
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { useNotifications } from "@/contexts/notification-context"

interface SystemAlert {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  dismissible?: boolean
}

const alertIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
}

const alertVariants = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'destructive',
} as const

export function SystemAlerts() {
  const { showToast } = useNotifications()
  const [alerts, setAlerts] = React.useState<SystemAlert[]>([
    {
      id: '1',
      type: 'success',
      title: 'System Healthy',
      message: 'All services are running normally. Last health check: 2 minutes ago.',
      dismissible: true
    },
    {
      id: '2',
      type: 'warning',
      title: 'High Memory Usage',
      message: 'Memory usage is at 85%. Consider optimizing queries or scaling resources.',
      dismissible: true
    },
    {
      id: '3',
      type: 'info',
      title: 'Maintenance Scheduled',
      message: 'System maintenance is scheduled for tonight at 2:00 AM UTC. Expected downtime: 30 minutes.',
      dismissible: true
    }
  ])

  const dismissAlert = (id: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id))
    showToast('Alert dismissed', 'info')
  }

  const testNotifications = () => {
    const testTypes: Array<'info' | 'success' | 'warning' | 'error'> = ['info', 'success', 'warning', 'error']
    const randomType = testTypes[Math.floor(Math.random() * testTypes.length)]
    
    showToast(`Test ${randomType} notification`, randomType)
  }

  if (alerts.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">System Alerts</h3>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={testNotifications}
          className="text-xs"
        >
          Test Notifications
        </Button>
      </div>
      
      {alerts.map((alert) => {
        const Icon = alertIcons[alert.type]
        const variant = alertVariants[alert.type]
        
        return (
          <Alert key={alert.id} variant={variant as any}>
            <Icon className="h-4 w-4" />
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <AlertTitle>{alert.title}</AlertTitle>
                <AlertDescription>{alert.message}</AlertDescription>
              </div>
              {alert.dismissible && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => dismissAlert(alert.id)}
                  className="h-6 w-6 p-0 ml-2"
                >
                  <X className="h-3 w-3" />
                  <span className="sr-only">Dismiss alert</span>
                </Button>
              )}
            </div>
          </Alert>
        )
      })}
    </div>
  )
}
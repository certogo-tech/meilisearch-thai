"use client"

import * as React from "react"
import { toast } from "sonner"
import { Notification } from "@/types"

interface NotificationContextType {
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  dismissNotification: (id: string) => void
  showToast: (type: 'success' | 'error' | 'warning' | 'info', title: string, message?: string) => void
}

const NotificationContext = React.createContext<NotificationContextType | undefined>(undefined)

export function useNotifications() {
  const context = React.useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider')
  }
  return context
}

interface NotificationProviderProps {
  children: React.ReactNode
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [notifications, setNotifications] = React.useState<Notification[]>([
    {
      id: '1',
      type: 'success',
      title: 'System Update',
      message: 'Dictionary has been successfully updated with 5 new compound words',
      timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
      read: false,
    },
    {
      id: '2',
      type: 'info',
      title: 'Performance Report',
      message: 'Weekly tokenization performance report is now available',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      read: false,
    },
    {
      id: '3',
      type: 'warning',
      title: 'High Memory Usage',
      message: 'System memory usage is at 85%. Consider optimizing queries.',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
      read: true,
    },
  ])

  const addNotification = React.useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now().toString(),
      timestamp: new Date(),
      read: false,
    }
    
    setNotifications(prev => [newNotification, ...prev])
    
    // Also show as toast
    showToast(notification.type, notification.title, notification.message)
  }, [])

  const markAsRead = React.useCallback((id: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, read: true }
          : notification
      )
    )
  }, [])

  const markAllAsRead = React.useCallback(() => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    )
  }, [])

  const dismissNotification = React.useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id))
  }, [])

  const showToast = React.useCallback((
    type: 'success' | 'error' | 'warning' | 'info', 
    title: string, 
    message?: string
  ) => {
    const content = message ? `${title}: ${message}` : title
    
    switch (type) {
      case 'success':
        toast.success(content)
        break
      case 'error':
        toast.error(content)
        break
      case 'warning':
        toast.warning(content)
        break
      case 'info':
        toast.info(content)
        break
    }
  }, [])

  // Simulate real-time notifications (in production, this would come from WebSocket or SSE)
  React.useEffect(() => {
    const interval = setInterval(() => {
      // Randomly add a notification every 30 seconds (for demo purposes)
      if (Math.random() < 0.1) { // 10% chance every 30 seconds
        const demoNotifications = [
          {
            type: 'info' as const,
            title: 'New API Request',
            message: 'Tokenization request processed successfully',
          },
          {
            type: 'success' as const,
            title: 'Compound Word Added',
            message: 'New compound word "ราเมน" has been added to the dictionary',
          },
          {
            type: 'warning' as const,
            title: 'Rate Limit Warning',
            message: 'API rate limit approaching for user session',
          },
        ]
        
        const randomNotification = demoNotifications[Math.floor(Math.random() * demoNotifications.length)]
        addNotification(randomNotification)
      }
    }, 30000) // Check every 30 seconds

    return () => clearInterval(interval)
  }, [addNotification])

  const value = React.useMemo(() => ({
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    showToast,
  }), [notifications, addNotification, markAsRead, markAllAsRead, dismissNotification, showToast])

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}
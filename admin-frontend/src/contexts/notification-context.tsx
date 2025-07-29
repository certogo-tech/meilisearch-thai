"use client"

import * as React from "react"
import { toast } from "sonner"

export interface Notification {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  timestamp: Date
  read: boolean
  actionUrl?: string
  actionLabel?: string
}

interface NotificationContextType {
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  removeNotification: (id: string) => void
  clearAll: () => void
  unreadCount: number
  showToast: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
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
      title: 'System Update',
      message: 'New compound word added to dictionary',
      type: 'success',
      timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
      read: false,
      actionUrl: '/dictionary',
      actionLabel: 'View Dictionary'
    },
    {
      id: '2',
      title: 'Health Check',
      message: 'System health check completed successfully',
      type: 'info',
      timestamp: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
      read: false
    },
    {
      id: '3',
      title: 'User Activity',
      message: 'New user registered: editor@example.com',
      type: 'info',
      timestamp: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
      read: true,
      actionUrl: '/admin/users',
      actionLabel: 'Manage Users'
    }
  ])

  const addNotification = React.useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false
    }
    
    setNotifications(prev => [newNotification, ...prev])
    
    // Also show as toast
    showToast(notification.message, notification.type)
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

  const removeNotification = React.useCallback((id: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id))
  }, [])

  const clearAll = React.useCallback(() => {
    setNotifications([])
  }, [])

  const showToast = React.useCallback((message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
    switch (type) {
      case 'success':
        toast.success(message)
        break
      case 'error':
        toast.error(message)
        break
      case 'warning':
        toast.warning(message)
        break
      default:
        toast(message)
        break
    }
  }, [])

  const unreadCount = React.useMemo(() => 
    notifications.filter(n => !n.read).length, 
    [notifications]
  )

  const value = React.useMemo(() => ({
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    unreadCount,
    showToast
  }), [
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    unreadCount,
    showToast
  ])

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}
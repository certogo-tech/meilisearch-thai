"use client"

import * as React from "react"
import { Bell, Check, X, AlertCircle, Info, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import { Notification } from "@/types"

interface NotificationCenterProps {
  notifications: Notification[]
  onMarkAsRead: (id: string) => void
  onMarkAllAsRead: () => void
  onDismiss: (id: string) => void
}

const notificationIcons = {
  success: Check,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const notificationColors = {
  success: "text-green-600 bg-green-50 border-green-200",
  error: "text-red-600 bg-red-50 border-red-200",
  warning: "text-yellow-600 bg-yellow-50 border-yellow-200",
  info: "text-blue-600 bg-blue-50 border-blue-200",
}

export function NotificationCenter({
  notifications,
  onMarkAsRead,
  onMarkAllAsRead,
  onDismiss,
}: NotificationCenterProps) {
  const unreadCount = notifications.filter(n => !n.read).length
  const [isOpen, setIsOpen] = React.useState(false)

  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  const handleMarkAsRead = (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    onMarkAsRead(id)
  }

  const handleDismiss = (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    onDismiss(id)
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0 relative">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs flex items-center justify-center"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
          <span className="sr-only">
            {unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <Card className="border-0 shadow-none">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">Notifications</CardTitle>
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onMarkAllAsRead}
                  className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                >
                  Mark all as read
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No notifications</p>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                {notifications.map((notification) => {
                  const Icon = notificationIcons[notification.type]
                  
                  return (
                    <div
                      key={notification.id}
                      className={cn(
                        "border-b border-border p-4 hover:bg-muted/50 transition-colors",
                        !notification.read && "bg-muted/30"
                      )}
                    >
                      <div className="flex items-start space-x-3">
                        <div className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-full border",
                          notificationColors[notification.type]
                        )}>
                          <Icon className="h-4 w-4" />
                        </div>
                        
                        <div className="flex-1 space-y-1">
                          <div className="flex items-start justify-between">
                            <div className="space-y-1">
                              <p className="text-sm font-medium leading-none">
                                {notification.title}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {notification.message}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {formatTimestamp(notification.timestamp)}
                              </p>
                            </div>
                            
                            <div className="flex items-center space-x-1">
                              {!notification.read && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => handleMarkAsRead(notification.id, e)}
                                  className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                                >
                                  <Check className="h-3 w-3" />
                                  <span className="sr-only">Mark as read</span>
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => handleDismiss(notification.id, e)}
                                className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                              >
                                <X className="h-3 w-3" />
                                <span className="sr-only">Dismiss</span>
                              </Button>
                            </div>
                          </div>
                          
                          {!notification.read && (
                            <div className="flex">
                              <div className="h-2 w-2 rounded-full bg-blue-500" />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </PopoverContent>
    </Popover>
  )
}
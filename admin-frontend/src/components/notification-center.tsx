"use client"

import * as React from "react"
import Link from "next/link"
import { formatDistanceToNow } from "date-fns"
import { 
  Bell, 
  Check, 
  CheckCheck, 
  Trash2, 
  ExternalLink,
  Info,
  CheckCircle,
  AlertTriangle,
  XCircle
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { useNotifications, type Notification } from "@/contexts/notification-context"
import { cn } from "@/lib/utils"

const notificationIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
}

const notificationColors = {
  info: "text-blue-500",
  success: "text-green-500",
  warning: "text-yellow-500",
  error: "text-red-500",
}

interface NotificationItemProps {
  notification: Notification
  onMarkAsRead: (id: string) => void
  onRemove: (id: string) => void
}

function NotificationItem({ notification, onMarkAsRead, onRemove }: NotificationItemProps) {
  const Icon = notificationIcons[notification.type]
  
  return (
    <div className={cn(
      "p-3 border-b last:border-b-0 transition-colors hover:bg-muted/50",
      !notification.read && "bg-blue-50/50 dark:bg-blue-950/20"
    )}>
      <div className="flex items-start space-x-3">
        <div className={cn("mt-0.5", notificationColors[notification.type])}>
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
                {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
              </p>
            </div>
            
            <div className="flex items-center space-x-1">
              {!notification.read && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onMarkAsRead(notification.id)}
                  className="h-6 w-6 p-0"
                >
                  <Check className="h-3 w-3" />
                  <span className="sr-only">Mark as read</span>
                </Button>
              )}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onRemove(notification.id)}
                className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-3 w-3" />
                <span className="sr-only">Remove notification</span>
              </Button>
            </div>
          </div>
          
          {notification.actionUrl && notification.actionLabel && (
            <div className="pt-2">
              <Link href={notification.actionUrl}>
                <Button variant="outline" size="sm" className="h-7 text-xs">
                  {notification.actionLabel}
                  <ExternalLink className="ml-1 h-3 w-3" />
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function NotificationCenter() {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead, 
    removeNotification, 
    clearAll 
  } = useNotifications()

  return (
    <Popover>
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
            Notifications {unreadCount > 0 && `(${unreadCount} unread)`}
          </span>
        </Button>
      </PopoverTrigger>
      
      <PopoverContent align="end" className="w-80 p-0">
        <Card className="border-0 shadow-none">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Notifications</CardTitle>
              <div className="flex items-center space-x-2">
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllAsRead}
                    className="h-7 text-xs"
                  >
                    <CheckCheck className="mr-1 h-3 w-3" />
                    Mark all read
                  </Button>
                )}
                {notifications.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearAll}
                    className="h-7 text-xs text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="mr-1 h-3 w-3" />
                    Clear all
                  </Button>
                )}
              </div>
            </div>
            {unreadCount > 0 && (
              <p className="text-xs text-muted-foreground">
                {unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
              </p>
            )}
          </CardHeader>
          
          <CardContent className="p-0">
            {notifications.length === 0 ? (
              <div className="p-8 text-center">
                <Bell className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  No notifications
                </p>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                {notifications.map((notification) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={markAsRead}
                    onRemove={removeNotification}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </PopoverContent>
    </Popover>
  )
}
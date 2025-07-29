"use client"

import { useEffect, useRef } from 'react'
import { useNotifications } from '@/contexts/notification-context'

export function useRealTimeNotifications() {
  const { addNotification } = useNotifications()
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const connectToSSE = () => {
      // Get auth token
      const token = localStorage.getItem('accessToken')
      if (!token) {
        console.log('No auth token available for SSE connection')
        return
      }

      try {
        // Create EventSource with auth header (note: EventSource doesn't support custom headers)
        // We'll use a different approach with fetch and ReadableStream
        const controller = new AbortController()
        
        fetch('/api/notifications/sse', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          signal: controller.signal,
        })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
          }
          
          if (!response.body) {
            throw new Error('No response body')
          }

          const reader = response.body.getReader()
          const decoder = new TextDecoder()

          const readStream = async () => {
            try {
              while (true) {
                const { done, value } = await reader.read()
                
                if (done) {
                  console.log('SSE stream ended')
                  break
                }

                const chunk = decoder.decode(value, { stream: true })
                const lines = chunk.split('\n')

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    try {
                      const data = JSON.parse(line.slice(6))
                      
                      if (data.type === 'connected') {
                        console.log('Connected to notification stream')
                      } else if (data.type === 'ping') {
                        // Keep-alive ping, ignore
                      } else if (data.id && data.title && data.message) {
                        // Valid notification
                        addNotification({
                          title: data.title,
                          message: data.message,
                          type: data.type || 'info'
                        })
                      }
                    } catch (error) {
                      console.error('Error parsing SSE data:', error)
                    }
                  }
                }
              }
            } catch (error) {
              console.error('Error reading SSE stream:', error)
            }
          }

          readStream()

          // Store the abort controller for cleanup
          eventSourceRef.current = { close: () => controller.abort() } as any
        })
        .catch(error => {
          console.error('SSE connection error:', error)
          
          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect to SSE...')
            connectToSSE()
          }, 5000)
        })

      } catch (error) {
        console.error('Failed to establish SSE connection:', error)
      }
    }

    // Initial connection
    connectToSSE()

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }
  }, [addNotification])

  return {
    // Could expose connection status here if needed
  }
}
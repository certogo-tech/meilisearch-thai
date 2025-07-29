import { NextRequest } from 'next/server'

// Store active connections
const connections = new Set<ReadableStreamDefaultController>()

// Simulate real-time events
const eventTypes = [
  { type: 'compound_added', title: 'Dictionary Update', message: 'New compound word added' },
  { type: 'user_login', title: 'User Activity', message: 'User logged in' },
  { type: 'system_health', title: 'System Status', message: 'Health check completed' },
  { type: 'bulk_import', title: 'Import Complete', message: 'Bulk import finished successfully' },
]

// Send periodic notifications
setInterval(() => {
  if (connections.size > 0) {
    const randomEvent = eventTypes[Math.floor(Math.random() * eventTypes.length)]
    const notification = {
      id: Math.random().toString(36).substr(2, 9),
      title: randomEvent.title,
      message: `${randomEvent.message} at ${new Date().toLocaleTimeString()}`,
      type: Math.random() > 0.8 ? 'warning' : Math.random() > 0.6 ? 'success' : 'info',
      timestamp: new Date().toISOString(),
    }

    const data = `data: ${JSON.stringify(notification)}\n\n`
    
    connections.forEach(controller => {
      try {
        controller.enqueue(new TextEncoder().encode(data))
      } catch (error) {
        // Connection closed, remove it
        connections.delete(controller)
      }
    })
  }
}, 30000) // Send notification every 30 seconds

export async function GET(request: NextRequest) {
  // Verify authentication
  const authHeader = request.headers.get('authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    return new Response('Unauthorized', { status: 401 })
  }

  const stream = new ReadableStream({
    start(controller) {
      // Add connection to active connections
      connections.add(controller)
      
      // Send initial connection message
      const welcomeMessage = `data: ${JSON.stringify({
        type: 'connected',
        message: 'Connected to notification stream'
      })}\n\n`
      
      controller.enqueue(new TextEncoder().encode(welcomeMessage))
      
      // Send keep-alive every 15 seconds
      const keepAlive = setInterval(() => {
        try {
          controller.enqueue(new TextEncoder().encode('data: {"type":"ping"}\n\n'))
        } catch (error) {
          clearInterval(keepAlive)
          connections.delete(controller)
        }
      }, 15000)
      
      // Clean up on close
      request.signal.addEventListener('abort', () => {
        clearInterval(keepAlive)
        connections.delete(controller)
        controller.close()
      })
    },
    
    cancel() {
      connections.delete(this as any)
    }
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control',
    },
  })
}
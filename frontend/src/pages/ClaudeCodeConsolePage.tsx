import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../utils/api'
import './ClaudeCodeConsolePage.css'
// Updated thinking stream UI

interface UserWithToken {
  user_id: string
  username: string
  email: string | null
  has_token: boolean
  token_id: string | null
  token_name: string | null
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  messageType?: 'thinking' | 'output' | 'user_question' // Type of assistant message
  isThinking?: boolean // For current streaming thinking message
}

interface StreamMessage {
  type: 'thought' | 'output' | 'error' | 'done' | 'status'
  content?: string
  thinking?: string
  output?: string
  error?: string
  status?: string
  timestamp: string
}

export function ClaudeCodeConsolePage() {
  const [users, setUsers] = useState<UserWithToken[]>([])
  const [selectedTokenId, setSelectedTokenId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const currentThinkingRef = useRef<string>('') // Current streaming thinking content
  const currentOutputRef = useRef<string>('') // Current streaming output content

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load users on mount
  useEffect(() => {
    loadUsers()
  }, [])

  // Connect WebSocket
  useEffect(() => {
    connectWebSocket()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const loadUsers = async () => {
    try {
      const data = await apiFetch<UserWithToken[]>('/debug/users-with-tokens')
      setUsers(data)

      // Auto-select first user with a token
      const firstWithToken = data.find(u => u.has_token)
      if (firstWithToken && firstWithToken.token_id) {
        setSelectedTokenId(firstWithToken.token_id)
      }
    } catch (err) {
      console.error('Failed to load users:', err)
      setError('Failed to load users')
    }
  }

  const connectWebSocket = () => {
    const token = localStorage.getItem('atc_token')
    if (!token) {
      setError('No auth token found')
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/ws/debug/claude-console?token=${token}`

    console.log('Connecting to WebSocket URL:', wsUrl)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setError(null)
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as StreamMessage
      handleStreamMessage(data)
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      setError('WebSocket connection error')
      setIsConnected(false)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      setIsStreaming(false)

      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          connectWebSocket()
        }
      }, 3000)
    }

    wsRef.current = ws
  }

  const handleStreamMessage = (msg: StreamMessage) => {
    switch (msg.type) {
      case 'status':
        console.log('Status:', msg.status)
        break

      case 'thought':
        // Update or create thinking message - thinking messages replace previous thinking
        console.log('🧠 THOUGHT MESSAGE RECEIVED (NEW CODE):', msg.content?.substring(0, 50))
        currentThinkingRef.current += (msg.content || msg.thinking || '')
        updateThinkingMessage()
        break

      case 'output':
        // When we get output, finalize any thinking message first
        if (currentThinkingRef.current) {
          finalizeThinkingMessage()
        }
        // Append to current output message
        currentOutputRef.current += (msg.content || msg.output || '')
        updateOutputMessage()
        break

      case 'error':
        setError(msg.error || 'Unknown error')
        setIsStreaming(false)
        break

      case 'done':
        // Finalize any pending messages
        if (currentThinkingRef.current) {
          finalizeThinkingMessage()
        }
        if (currentOutputRef.current) {
          finalizeOutputMessage()
        }
        setIsStreaming(false)
        currentThinkingRef.current = ''
        currentOutputRef.current = ''
        break
    }
  }

  const updateThinkingMessage = () => {
    setMessages(prev => {
      const newMessages = [...prev]
      const lastMessage = newMessages[newMessages.length - 1]

      // Update or create streaming thinking message
      if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isThinking) {
        // Update existing thinking message
        lastMessage.content = currentThinkingRef.current
        lastMessage.timestamp = new Date().toISOString()
      } else {
        // Create new thinking message
        newMessages.push({
          role: 'assistant',
          content: currentThinkingRef.current,
          timestamp: new Date().toISOString(),
          messageType: 'thinking',
          isThinking: true,
        })
      }

      return newMessages
    })
  }

  const finalizeThinkingMessage = () => {
    setMessages(prev => {
      const newMessages = [...prev]
      const lastMessage = newMessages[newMessages.length - 1]

      if (lastMessage && lastMessage.isThinking) {
        // Mark thinking as finalized
        lastMessage.isThinking = false
      }

      return newMessages
    })
    currentThinkingRef.current = ''
  }

  const updateOutputMessage = () => {
    setMessages(prev => {
      const newMessages = [...prev]
      const lastMessage = newMessages[newMessages.length - 1]

      // Update or create streaming output message
      if (lastMessage && lastMessage.role === 'assistant' && lastMessage.messageType === 'output' && !lastMessage.isThinking) {
        // Update existing output message
        lastMessage.content = currentOutputRef.current
        lastMessage.timestamp = new Date().toISOString()
      } else {
        // Create new output message
        newMessages.push({
          role: 'assistant',
          content: currentOutputRef.current,
          timestamp: new Date().toISOString(),
          messageType: 'output',
        })
      }

      return newMessages
    })
  }

  const finalizeOutputMessage = () => {
    currentOutputRef.current = ''
  }

  const handleSendMessage = () => {
    if (!inputText.trim() || !isConnected || isStreaming) {
      return
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputText,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsStreaming(true)
    setError(null)
    currentThinkingRef.current = ''
    currentOutputRef.current = ''

    // Send to WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = {
        type: 'chat',
        messages: [...messages, userMessage].map(m => ({
          role: m.role,
          content: m.content,
        })),
        use_token_id: selectedTokenId,
      }

      wsRef.current.send(JSON.stringify(payload))
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const clearMessages = () => {
    setMessages([])
    currentThinkingRef.current = ''
    currentOutputRef.current = ''
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h2>Claude Code Console</h2>
          <p className="page-subtitle">
            Debug interface for Claude Code integration
          </p>
        </div>
      </div>

      {error && (
        <div className="error-message" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <div className="console-container">
        {/* Top bar with controls */}
        <div className="console-controls">
          <div className="control-group">
            <label htmlFor="user-select">User Token:</label>
            <select
              id="user-select"
              value={selectedTokenId || ''}
              onChange={(e) => setSelectedTokenId(e.target.value || null)}
              disabled={isStreaming}
            >
              <option value="">Use pool rotation</option>
              {users.filter(u => u.has_token).map(user => (
                <option key={user.user_id} value={user.token_id || ''}>
                  {user.username} ({user.token_name})
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '● Connected' : '○ Disconnected'}
            </span>
          </div>

          <button
            className="btn-secondary"
            onClick={clearMessages}
            disabled={isStreaming}
          >
            Clear
          </button>
        </div>

        {/* Chat messages */}
        <div className="console-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>No messages yet. Start a conversation with Claude Code!</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.role} ${msg.messageType === 'thinking' ? 'message-thinking' : ''}`}>
              <div className="message-header">
                <strong>{msg.role === 'user' ? 'You' : 'Claude Code'}</strong>
                {msg.messageType === 'thinking' && <span className="thinking-label">(thinking)</span>}
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className={`message-content ${msg.messageType === 'thinking' ? 'thinking-content' : ''}`}>
                <pre>{msg.content}</pre>
              </div>
            </div>
          ))}

          {isStreaming && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
            <div className="message message-assistant">
              <div className="message-header">
                <strong>Claude Code</strong>
                <span className="streaming-indicator">Streaming...</span>
              </div>
              <div className="message-content">
                <div className="loading-spinner"></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="console-input">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
            disabled={!isConnected || isStreaming}
            rows={3}
          />
          <button
            onClick={handleSendMessage}
            disabled={!isConnected || isStreaming || !inputText.trim()}
            className="btn-primary"
          >
            {isStreaming ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}


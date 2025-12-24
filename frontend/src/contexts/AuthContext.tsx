import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react'

const TOKEN_KEY = 'atc_token'
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface User {
  id: string
  git_handle: string
  email: string
  display_name: string | null
  avatar_url: string | null
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  login: () => Promise<void>
  logout: () => void
  handleCallback: (code: string, state: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  )
  const [isLoading, setIsLoading] = useState(true)

  const fetchUser = useCallback(async (authToken: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/users/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem(TOKEN_KEY)
          setToken(null)
          setUser(null)
        }
        return
      }

      const userData = await response.json()
      setUser(userData)
    } catch {
      console.error('Failed to fetch user')
    }
  }, [])

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        await fetchUser(token)
      }
      setIsLoading(false)
    }
    initAuth()
  }, [token, fetchUser])

  const login = async () => {
    const callbackUrl = `${window.location.origin}/auth/callback`
    const response = await fetch(
      `${API_URL}/api/v1/auth/github?redirect_uri=${encodeURIComponent(callbackUrl)}`
    )

    if (!response.ok) {
      throw new Error('Failed to initiate OAuth flow')
    }

    const data = await response.json()
    sessionStorage.setItem('oauth_state', data.state)
    window.location.href = data.url
  }

  const handleCallback = async (code: string, state: string) => {
    const savedState = sessionStorage.getItem('oauth_state')
    if (savedState !== state) {
      throw new Error('Invalid OAuth state')
    }
    sessionStorage.removeItem('oauth_state')

    const callbackUrl = `${window.location.origin}/auth/callback`
    const response = await fetch(
      `${API_URL}/api/v1/auth/github/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&redirect_uri=${encodeURIComponent(callbackUrl)}`
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'OAuth callback failed')
    }

    const data = await response.json()
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
    await fetchUser(data.access_token)
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    handleCallback,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

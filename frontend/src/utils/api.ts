// Use relative URLs when VITE_API_URL is empty or not set (goes through nginx proxy)
// Only use direct backend URL for local development without nginx
const API_URL =
  typeof import.meta.env.VITE_API_URL === 'string'
    ? import.meta.env.VITE_API_URL || '/api/v1'
    : 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'atc_token'

interface FetchOptions extends RequestInit {
  skipAuth?: boolean
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, ...fetchOptions } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  }

  if (!skipAuth) {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      const h = headers as Record<string, string>
      h['Authorization'] = `Bearer ${token}`
    }
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    let data: unknown
    try {
      data = await response.json()
    } catch {
      data = null
    }

    const message =
      (data as { detail?: string })?.detail ||
      `Request failed with status ${response.status}`
    throw new ApiError(message, response.status, data)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export async function apiUploadFile<T>(
  endpoint: string,
  file: File,
  fieldName: string = 'file'
): Promise<T> {
  const formData = new FormData()
  formData.append(fieldName, file)

  const headers: HeadersInit = {}
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    let data: unknown
    try {
      data = await response.json()
    } catch {
      data = null
    }

    const message =
      (data as { detail?: string })?.detail ||
      `Upload failed with status ${response.status}`
    throw new ApiError(message, response.status, data)
  }

  return response.json()
}

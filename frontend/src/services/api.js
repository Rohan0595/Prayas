/**
 * API service — all backend calls live here.
 * Uses fetch with SSE for streaming.
 */

const BASE = '/api'

function getHeaders(customHeaders = {}) {
  const token = localStorage.getItem('omni_token')
  return {
    ...customHeaders,
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Login failed')
  return data
}

export async function register(email, password) {
  const res = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Registration failed')
  return data
}

export async function logout() {
  await fetch(`${BASE}/auth/logout`, { method: 'POST', headers: getHeaders() })
}


// ─── Sessions ─────────────────────────────────────────────────────────────

export async function listSessions() {
  const res = await fetch(`${BASE}/sessions`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch sessions')
  return res.json()
}

export async function createSession() {
  const res = await fetch(`${BASE}/sessions`, { method: 'POST', headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to create session')
  return res.json()
}

export async function deleteSession(id) {
  const res = await fetch(`${BASE}/sessions/${id}`, { method: 'DELETE', headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to delete session')
  return res.json()
}

export async function getSessionMessages(id) {
  const res = await fetch(`${BASE}/sessions/${id}/messages`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch messages')
  return res.json()
}

// ─── Streaming chat ────────────────────────────────────────────────────────

export function streamChat({ message, sessionId, model, useAgent, useRag, onChunk, onMeta, onDone, onError }) {
  const controller = new AbortController()

  const body = JSON.stringify({
    message,
    session_id: sessionId,
    model: model === 'auto' ? null : model,
    use_agent: useAgent,
    use_rag: useRag,
  })

  if (useAgent) {
    fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body,
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.text()
          onError?.(err)
          return
        }
        const data = await res.json()
        onMeta?.({ session_id: data.session_id, model: data.model_used })
        onChunk?.(data.reply)
        onDone?.()
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError?.(err.message)
      })
    return controller
  }

  fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.text()
        onError?.(err)
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (!raw) continue
          try {
            const event = JSON.parse(raw)
            if (event.type === 'meta') {
              const meta = JSON.parse(event.payload)
              onMeta?.(meta)
            } else if (event.type === 'chunk') {
              onChunk?.(event.payload)
            } else if (event.type === 'done') {
              onDone?.()
            } else if (event.type === 'error') {
              onError?.(event.payload)
            }
          } catch { /* skip malformed */ }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError?.(err.message)
    })

  return controller
}

// ─── Document upload ───────────────────────────────────────────────────────

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { 
    method: 'POST', 
    body: form,
    headers: getHeaders()
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Upload failed')
  return data
}

export async function getUploadStatus() {
  const res = await fetch(`${BASE}/upload/status`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch upload status')
  return res.json()
}

export async function listDocuments() {
  const res = await fetch(`${BASE}/upload/documents`, { headers: getHeaders() })
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function deleteDocument(filename) {
  const res = await fetch(`${BASE}/upload/documents/${filename}`, { 
    method: 'DELETE',
    headers: getHeaders()
  })
  if (!res.ok) throw new Error('Failed to delete document')
  return res.json()
}

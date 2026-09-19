const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_URL = `${API_BASE_URL}/analyze-change`
const CHAT_API_URL = `${API_BASE_URL}/chat`
const HISTORY_API_URL = `${API_BASE_URL}/history`

export async function analyzeChange(changeDescription) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ change_description: changeDescription }),
  })

  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const message =
      payload?.detail ??
      (response.status >= 500
        ? 'The analysis server encountered an error. Please try again.'
        : 'Unable to analyze this change. Please check your input and try again.')
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }

  return payload
}

export async function sendChatFollowup(message, chatHistory, currentAnalysis) {
  const response = await fetch(CHAT_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      chat_history: chatHistory,
      current_analysis: currentAnalysis,
    }),
  })

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail || 'Unable to answer the follow-up question.')
  }

  return payload.response
}

export async function getAnalysisHistory() {
  const response = await fetch(HISTORY_API_URL)
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail || 'Unable to load recent analyses.')
  }
  return payload
}

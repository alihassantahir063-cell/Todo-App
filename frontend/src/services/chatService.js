import { api } from './api'

export const chatService = {
  send: (message, conversationId) => api.post('/chat/message', {
    message,
    conversation_id: conversationId || null,
  }, { timeout: 135000 }).then((response) => response.data),
  reset: (conversationId) => api.delete(`/chat/conversations/${conversationId}`),
}

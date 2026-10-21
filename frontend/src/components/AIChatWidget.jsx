import { useEffect, useRef, useState } from 'react'
import { Bot, LoaderCircle, RotateCcw, Send, Sparkles, X } from 'lucide-react'
import { chatService } from '../services/chatService'
import './AIChatWidget.css'

const suggestions = ['Show pending tasks', 'Create a task', 'Show my task summary']

function restoreSession(userId) {
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(`daymark-chat-${userId}`) || '{}')
    return {
      conversationId: typeof saved.conversationId === 'string' ? saved.conversationId : null,
      messages: Array.isArray(saved.messages)
        ? saved.messages.filter((message) => ['user', 'assistant'].includes(message.role) && typeof message.content === 'string').slice(-24)
        : [],
      warning: '',
    }
  } catch {
    return { conversationId: null, messages: [], warning: 'This tab could not restore its saved chat session.' }
  }
}

function actionSummary(action) {
  const data = action.data || {}
  if (action.type === 'task_created') return `Created: ${data.title}`
  if (action.type === 'task_updated') return `Updated: ${data.title}`
  if (action.type === 'task_status') return `${data.title}: ${data.status}`
  if (action.type === 'task_deleted') return `Deleted: ${data.title}`
  if (action.type === 'user_status') return `${data.name || 'Account'}: ${data.is_active ? 'active' : 'inactive'}`
  if (action.type === 'admin_task_deleted') return `Deleted: ${data.title}`
  if (action.type === 'confirmation_required') return `Confirmation required: ${data.title || data.name || 'selected record'}`
  return null
}

function ActionResults({ actions = [] }) {
  if (!actions.length) return null
  return <div className="chat-action-results">
    {actions.map((action, index) => {
      const summary = actionSummary(action)
      const items = action.items || []
      const data = action.data || {}
      return <section className="chat-action" key={`${action.type}-${index}`}>
        {summary && <strong>{summary}</strong>}
        {['task_statistics', 'user_task_statistics'].includes(action.type) && <p>
          {data.total} total · {data.pending} pending · {data.completed} completed · {data.overdue} overdue
        </p>}
        {action.type === 'system_statistics' && <p>
          {data.total_users} users · {data.total_tasks} tasks · {data.pending_tasks} pending · {data.completed_tasks} completed
        </p>}
        {items.length > 0 && <ul>
          {items.map((item) => <li key={`${item.id}-${item.title || item.name}`}>
            <span>{item.title || item.name || item.email}</span>
            {item.status && <small>{item.status}</small>}
            {item.priority && <small>{item.priority} priority</small>}
            {item.due_date && <small>Due {item.due_date}</small>}
            {item.owner && <small>Owner: {item.owner.name}</small>}
          </li>)}
        </ul>}
        {action.type.endsWith('_list') && items.length === 0 && <p>No matching records.</p>}
      </section>
    })}
  </div>
}

function InlineText({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={index}>{part.slice(1, -1)}</em>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index}>{part.slice(1, -1)}</code>
    }
    return part
  })
}

function FormattedReply({ content }) {
  const blocks = []
  let paragraph = []
  let list = []

  function flushParagraph() {
    if (!paragraph.length) return
    blocks.push(<p key={`p-${blocks.length}`}><InlineText text={paragraph.join(' ')} /></p>)
    paragraph = []
  }

  function flushList() {
    if (!list.length) return
    blocks.push(
      <ul key={`ul-${blocks.length}`}>
        {list.map((item, index) => <li key={index}><InlineText text={item} /></li>)}
      </ul>,
    )
    list = []
  }

  content.split(/\r?\n/).forEach((line) => {
    const heading = line.match(/^\s{0,3}#{1,3}\s+(.+)$/)
    const unordered = line.match(/^\s*[-*+]\s+(.+)$/)
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/)

    if (unordered || ordered) {
      flushParagraph()
      list.push((unordered || ordered)[1])
      return
    }

    flushList()
    if (!line.trim()) {
      flushParagraph()
      return
    }

    if (heading) {
      flushParagraph()
      blocks.push(<p key={`h-${blocks.length}`}><strong><InlineText text={heading[1]} /></strong></p>)
      return
    }
    paragraph.push(line.trim())
  })

  flushList()
  flushParagraph()
  return blocks
}

function Message({ message }) {
  const isUser = message.role === 'user'
  return <article className={`chat-message ${isUser ? 'from-user' : 'from-assistant'}`}>
    {!isUser && <span className="chat-message-avatar"><Sparkles size={14} /></span>}
    <div className="chat-message-content">
      <div className="chat-bubble"><FormattedReply content={message.content} /></div>
      {!isUser && <ActionResults actions={message.actions} />}
      <time dateTime={message.timestamp}>{new Date(message.timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</time>
    </div>
  </article>
}

export default function AIChatWidget({ userId }) {
  const [initialSession] = useState(() => restoreSession(userId))
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState(initialSession.messages)
  const [conversationId, setConversationId] = useState(initialSession.conversationId)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [storageWarning, setStorageWarning] = useState(initialSession.warning)
  const endRef = useRef(null)
  const inputRef = useRef(null)
  const conversationRef = useRef(null)
  const busyRef = useRef(false)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  useEffect(() => {
    try {
      window.sessionStorage.setItem(`daymark-chat-${userId}`, JSON.stringify({
        conversationId,
        messages: messages.slice(-24),
      }))
    } catch {
      setStorageWarning('This tab could not save the chat session; its history may not survive a refresh.')
    }
  }, [conversationId, messages, userId])

  async function sendMessage(value = draft) {
    const text = value.trim()
    if (!text || busyRef.current) return
    const userMessage = { role: 'user', content: text, timestamp: new Date().toISOString() }
    busyRef.current = true
    setBusy(true)
    setError('')
    setDraft('')
    setMessages((current) => [...current, userMessage])
    try {
      const result = await chatService.send(text, conversationRef.current)
      conversationRef.current = result.conversation_id
      setConversationId(result.conversation_id)
      if ((result.actions || []).some((action) => [
        'task_created', 'task_updated', 'task_status', 'task_deleted',
        'admin_task_deleted', 'user_status',
      ].includes(action.type))) {
        window.dispatchEvent(new Event('daymark:data-changed'))
      }
      setMessages((current) => [...current, {
        role: 'assistant',
        content: result.reply,
        actions: result.actions || [],
        timestamp: new Date().toISOString(),
      }])
    } catch (requestError) {
      const detail = requestError.response?.data?.detail
      const message = typeof detail === 'string' ? detail : 'The assistant is unavailable right now. Please try again.'
      setError(message)
      setMessages((current) => [...current, {
        role: 'assistant',
        content: message,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  async function resetConversation() {
    if (!window.confirm('Clear this conversation and start a new one?')) return
    setError('')
    if (conversationRef.current) {
      try {
        await chatService.reset(conversationRef.current)
      } catch (requestError) {
        const detail = requestError.response?.data?.detail
        setError(typeof detail === 'string' ? detail : 'The conversation could not be cleared.')
        return
      }
    }
    conversationRef.current = null
    setConversationId(null)
    setMessages([])
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendMessage()
    }
  }

  return <>
    {open && <section className="ai-chat-window" aria-label="AI chat assistant">
      <header className="ai-chat-header">
        <span className="ai-chat-brand-icon"><Bot size={20} /></span>
        <div className="ai-chat-heading">
          <strong>Daymark assistant</strong>
          <span><i className={busy ? 'is-busy' : ''} />{busy ? 'Working…' : 'Ready to help'}</span>
        </div>
        <div className="ai-chat-header-actions">
          <button type="button" className="ai-chat-icon" aria-label="Clear conversation" title="Clear conversation" onClick={resetConversation} disabled={busy}><RotateCcw size={17} /></button>
          <button type="button" className="ai-chat-icon" aria-label="Close chat" title="Minimize chat" onClick={() => setOpen(false)}><X size={19} /></button>
        </div>
      </header>
      <div className="ai-chat-messages" aria-live="polite" aria-relevant="additions text">
        {messages.length === 0 && <div className="ai-chat-welcome">
          <span className="ai-chat-welcome-icon"><Sparkles size={21} /></span>
          <strong>What can I help you with?</strong>
          <p>Ask me about your tasks or tell me what you’d like to do.</p>
          <div className="ai-chat-suggestions">
            {suggestions.map((suggestion) => <button key={suggestion} type="button" onClick={() => sendMessage(suggestion)} disabled={busy}>{suggestion}</button>)}
          </div>
        </div>}
        {messages.map((message, index) => <Message key={`${message.timestamp}-${index}`} message={message} />)}
        {busy && <div className="chat-thinking" role="status"><LoaderCircle size={15} className="chat-spinner" /> Thinking…</div>}
        <div ref={endRef} />
      </div>
      {error && <div className="ai-chat-error" role="alert">{error}</div>}
      {storageWarning && <div className="ai-chat-error" role="status">{storageWarning}</div>}
      <form className="ai-chat-composer" onSubmit={(event) => { event.preventDefault(); sendMessage() }}>
        <textarea
          ref={inputRef}
          aria-label="Message the assistant"
          placeholder="Message Daymark…"
          value={draft}
          rows={1}
          maxLength={2000}
          disabled={busy}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button type="submit" aria-label="Send message" disabled={busy || !draft.trim()}><Send size={17} /></button>
        <span className="ai-chat-hint">Enter to send · Shift+Enter for a new line</span>
      </form>
    </section>}
    <button
      type="button"
      className={`ai-chat-launcher ${open ? 'is-open' : ''}`}
      aria-label={open ? 'Chat assistant is open' : 'Open AI chat assistant'}
      aria-expanded={open}
      title={open ? 'Chat assistant' : 'Ask Daymark'}
      onClick={() => setOpen((value) => !value)}
    >
      {open ? <X size={23} /> : <Bot size={24} />}
      {!open && <span className="ai-chat-launcher-tooltip">Ask Daymark</span>}
    </button>
  </>
}

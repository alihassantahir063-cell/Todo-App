export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!error?.response) return 'Could not connect to the server. Check your connection and try again.'
  const detail = error.response.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join(' → ') : ''
      return location ? `${location}: ${item.msg}` : item.msg
    })
    return messages.join(' · ') || fallback
  }
  return fallback
}

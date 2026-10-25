import { useEffect } from 'react'
import { taskService } from '../services/taskService'

function loadNotifiedReminders(storageKey) {
  try {
    const stored = localStorage.getItem(storageKey)
    const keys = stored ? JSON.parse(stored) : []
    if (!Array.isArray(keys)) throw new TypeError('Expected a reminder key list')
    return new Set(keys.filter((key) => typeof key === 'string'))
  } catch (error) {
    console.error('Could not read saved reminder notifications.', error)
    return new Set()
  }
}

function saveNotifiedReminders(storageKey, reminders) {
  try {
    localStorage.setItem(storageKey, JSON.stringify([...reminders].slice(-500)))
  } catch (error) {
    console.error('Could not save reminder notification state.', error)
  }
}

export default function ReminderNotifications({ userId }) {
  useEffect(() => {
    if (!userId || !('Notification' in window)) return undefined

    const storageKey = `daymark-reminders:${userId}`
    const notified = loadNotifiedReminders(storageKey)
    let checking = false

    const checkReminders = async () => {
      if (checking || Notification.permission !== 'granted') return
      checking = true
      try {
        const reminders = await taskService.remindersDue()
        for (const task of reminders) {
          if (!task.reminder_at) continue
          const key = `${task.id}:${task.reminder_at}`
          if (notified.has(key)) continue

          const notification = new Notification('Task reminder', {
            body: task.title,
            tag: `daymark-${key}`,
          })
          notification.onclick = () => {
            window.focus()
            window.location.assign('/tasks')
          }
          notified.add(key)
          saveNotifiedReminders(storageKey, notified)
        }
      } catch (error) {
        console.error('Could not check for task reminders.', error)
      } finally {
        checking = false
      }
    }

    const onFocus = () => { void checkReminders() }
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') void checkReminders()
    }
    void checkReminders()
    const intervalId = window.setInterval(() => { void checkReminders() }, 60_000)
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      window.clearInterval(intervalId)
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [userId])

  return null
}

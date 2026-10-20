import { createContext, useEffect, useMemo, useState } from 'react'

export const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('todo-theme') || 'light')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('todo-theme', theme)
  }, [theme])
  const value = useMemo(() => ({ theme, toggleTheme: () => setTheme((current) => current === 'dark' ? 'light' : 'dark') }), [theme])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

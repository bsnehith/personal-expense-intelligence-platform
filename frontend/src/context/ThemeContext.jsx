import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'expense-theme'

const ThemeContext = createContext(null)

function getSystemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'system'
    } catch {
      return 'system'
    }
  })

  const [systemDark, setSystemDark] = useState(() =>
    typeof window !== 'undefined' ? getSystemPrefersDark() : true,
  )

  useEffect(() => {
    if (theme !== 'system') return undefined
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => setSystemDark(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [theme])

  const effective = useMemo(() => {
    if (theme === 'system') return systemDark ? 'dark' : 'light'
    return theme
  }, [theme, systemDark])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', effective === 'dark')
  }, [effective])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  const setTheme = useCallback((next) => {
    setThemeState(next)
  }, [])

  const value = useMemo(
    () => ({ theme, setTheme, effective }),
    [theme, setTheme, effective],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

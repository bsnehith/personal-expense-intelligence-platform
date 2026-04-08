import { useEffect, useRef, useState } from 'react'

/**
 * Emits updates at most once per `intervalMs` while `value` changes (trailing throttle).
 * Reduces expensive downstream work (e.g. charts) during rapid stream updates.
 */
export function useThrottledValue(value, intervalMs) {
  const [out, setOut] = useState(value)
  const lastEmit = useRef(0)
  const timeoutRef = useRef(null)
  const latestRef = useRef(value)

  useEffect(() => {
    latestRef.current = value

    const now = Date.now()
    const since = now - lastEmit.current

    const flush = () => {
      lastEmit.current = Date.now()
      setOut(latestRef.current)
      timeoutRef.current = null
    }

    if (since >= intervalMs) {
      flush()
      return undefined
    }

    if (!timeoutRef.current) {
      timeoutRef.current = window.setTimeout(flush, intervalMs - since)
    }

    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
    }
  }, [value, intervalMs])

  return out
}

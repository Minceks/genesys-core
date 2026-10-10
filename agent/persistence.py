"""Browser persistence helper for independent user applications."""

PERSISTENT_STATE_SOURCE = '''import { useEffect, useState } from 'react'

// Store ordinary application data only, never passwords or API secrets.
export function usePersistentState(key, initialValue) {
  const storageKey = 'user-app:v1:' + key
  const [storageError, setStorageError] = useState('')
  const [value, setValue] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved !== null) return JSON.parse(saved)
    } catch { /* Invalid/unavailable storage falls back to the initial value. */ }
    return typeof initialValue === 'function' ? initialValue() : initialValue
  })
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(value))
      setStorageError('')
    } catch { setStorageError('Changes could not be saved on this device. Keep this page open and check browser storage settings.') }
  }, [storageKey, value])
  return [value, setValue, storageError]
}
'''

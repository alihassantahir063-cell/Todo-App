import { useEffect } from 'react'

export function useDataRefresh(callback) {
  useEffect(() => {
    window.addEventListener('daymark:data-changed', callback)
    return () => window.removeEventListener('daymark:data-changed', callback)
  }, [callback])
}

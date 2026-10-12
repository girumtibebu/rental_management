const parse = (value) => new Date(String(value).replace(' ', 'T'))

export function timeAgo(value) {
  if (!value) return ''
  const seconds = (Date.now() - parse(value).getTime()) / 1000
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return parse(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: '2-digit' })
}

export function fullDate(value) {
  return value
    ? parse(value).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : ''
}

export function shortDate(value) {
  return value ? parse(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''
}

export const number = (value) => Number(value || 0).toLocaleString()

export const userName = (user) => (user || '').split('@')[0]

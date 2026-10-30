type Turn = { role: 'user' | 'bot'; text: string }

const MODE_PREFIX = /^\/(build|plan|discuss)\s+/i

export function savedPrompt(prompt: unknown) {
  return String(prompt ?? '').replace(MODE_PREFIX, '')
}

/** Combine server history with this tab's turns, which may already include the same jobs. */
export function mergeHistory<T extends Turn>(saved: T[], local: T[]): T[] {
  if (!local.length) return saved
  if (!saved.length) return local
  for (let overlap = Math.min(saved.length, local.length); overlap > 0; overlap--) {
    const tail = saved.slice(-overlap)
    if (tail.every((turn, index) => turn.role === local[index].role && turn.text === local[index].text)) {
      return [...saved.slice(0, -overlap), ...local]
    }
  }
  // Local turns carry richer metadata when they already begin with the saved conversation.
  if (local[0].text === saved[0].text) return local
  return [...saved, ...local]
}

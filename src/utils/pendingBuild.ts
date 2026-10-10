export type PendingBuild = { jobId: string; prompt: string; startedAt: number }
const key = (projectId: string) => `genesys:pending-build:${projectId}`
const handledKey = (projectId: string) => `genesys:handled-build:${projectId}`

export function pendingBuild(projectId: string): PendingBuild | null {
  try {
    const value = JSON.parse(localStorage.getItem(key(projectId)) || 'null')
    if (value && typeof value.jobId === 'string' && typeof value.prompt === 'string' &&
        Number.isFinite(value.startedAt) && Date.now() - value.startedAt < 86400000) return value
    localStorage.removeItem(key(projectId))
  } catch { /* Server lookup also supports unavailable browser storage. */ }
  return null
}

export function savePendingBuild(projectId: string, build: PendingBuild) {
  try { localStorage.setItem(key(projectId), JSON.stringify(build)) } catch { /* Recover from server instead. */ }
}

export function clearPendingBuild(projectId: string) {
  try { localStorage.removeItem(key(projectId)) } catch { /* Storage may be unavailable. */ }
}

export function handledBuild(projectId: string, jobId: string) {
  try { return localStorage.getItem(handledKey(projectId)) === jobId } catch { return false }
}

export function markBuildHandled(projectId: string, jobId: string) {
  clearPendingBuild(projectId)
  try { localStorage.setItem(handledKey(projectId), jobId) } catch { /* Storage may be unavailable. */ }
}

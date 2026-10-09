let currentProject: string | undefined;

export function getBetaProjectId(): string {
  if (currentProject) return currentProject;
  let stored: string | null = null;
  try { stored = localStorage.getItem("genesys_beta_project"); } catch { /* Use this session's in-memory project. */ }
  currentProject = stored && /^beta-[0-9a-f-]{36}$/.test(stored)
    ? stored : `beta-${crypto.randomUUID()}`;
  try { localStorage.setItem("genesys_beta_project", currentProject); } catch { /* Storage may be unavailable in private browsing. */ }
  return currentProject;
}

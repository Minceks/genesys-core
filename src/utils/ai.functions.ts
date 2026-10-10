import type { PendingBuild } from './pendingBuild';
import { getBetaProjectId } from "./project";
import { getAccessToken } from '../lib/supabase';
import { pendingBuild, savePendingBuild, clearPendingBuild, handledBuild, markBuildHandled } from './pendingBuild';

export async function recoverBackgroundBuild(projectId: string) {
  const saved = pendingBuild(projectId);
  if (saved) return saved;
  try {
    const response = await fetch(`${CLOUD_AGENT_URL}/agent/jobs?projectId=${encodeURIComponent(projectId)}`, {
      headers: buildCloudAgentHeaders(), signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) return null;
    const { job } = await response.json();
    if (!job?.jobId || !job.prompt || (job.state !== 'running' && handledBuild(projectId, job.jobId))) return null;
    const build = { jobId: job.jobId, prompt: job.prompt, startedAt: job.createdAt || Date.now() };
    savePendingBuild(projectId, build);
    return build;
  } catch { return null; }
}

// ============================================================
// GeneSys frontend agent client
// ============================================================
//
// Local development:
//   http://127.0.0.1:5000
//
// Production:
//   Railway backend
//
// You can override either environment with:
//   VITE_CLOUD_AGENT_URL
// ============================================================

const API_KEY = (import.meta.env.VITE_CLOUD_AGENT_API_KEY || "").trim();

const LOCAL_AGENT_URL =
  "http://127.0.0.1:5000";

const PRODUCTION_AGENT_URL =
  "https://remarkable-generosity-production-7d5a.up.railway.app";

export const CLOUD_AGENT_URL = (
  import.meta.env.VITE_CLOUD_AGENT_URL ||
  (import.meta.env.DEV
    ? LOCAL_AGENT_URL
    : PRODUCTION_AGENT_URL)
).replace(/\/+$/, "");

export function buildCloudAgentHeaders(
  includeJson = false,
): Record<string, string> {
  return {
    ...(includeJson ? { "Content-Type": "application/json" } : {}),
    ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
    ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
  };
}


// ============================================================
// TYPES
// ============================================================

export type AgentStep = {
  tool?: string;
  status?: string;
  result?: {
    status?: string;
    success?: boolean;
    url?: string | null;
    output?: string;
    file?: string;
    action?: string;
    message?: string;
    [key: string]: unknown;
  };
};

export type GenesysAgentResponse = {
  requestType: "chat" | "build";
  text: string;
  agent: string;
  steps: AgentStep[];
  modifiedFiles: string[];
  buildAttempted: boolean;
  buildPassed: boolean;
  browserVerified: boolean;
  checkpointId: string | null;
  checkpointStatus: string | null;
  promotionToken: string | null;
  previewUrl: string | null;
  previewStarted?: boolean;
  status: string;
};


// ============================================================
// ERROR HELPER
// ============================================================

async function getErrorMessage(
  response: Response
): Promise<string> {
  try {
    const data = await response.json();

    if (
      data &&
      typeof data.message === "string"
    ) {
      if (response.status === 429 && Number.isFinite(data.retryAfter)) {
        const seconds = Math.max(1, Math.ceil(data.retryAfter));
        const wait = seconds < 60 ? `${seconds} seconds` : seconds < 3600 ? `${Math.ceil(seconds / 60)} minutes` : `${Math.ceil(seconds / 3600)} hours`;
        return `${data.message} Try again in ${wait}.`;
      }
      return data.message;
    }

    if (
      data &&
      typeof data.error === "string"
    ) {
      return data.error;
    }
  } catch {
    // Response was not JSON.
  }

  return `GeneSys agent request failed (${response.status} ${response.statusText})`;
}


// ============================================================
// ASK GENESYS
// ============================================================

export async function askGenesys(
  prompt: string,
  history: Array<{ role: "user" | "assistant"; content: string }> = [],
  onProgress?: (stage: string, requestId: string) => void,
  projectId = getBetaProjectId(),
  resumeBuild?: PendingBuild,
): Promise<GenesysAgentResponse> {
  const cleanedPrompt = prompt.trim();

  if (!cleanedPrompt) {
    throw new Error(
      "GeneSys request cannot be empty."
    );
  }

  const url =
    `${CLOUD_AGENT_URL}/agent/jobs`;

  try {
    const saved = resumeBuild || pendingBuild(projectId);
    const response = await fetch(
      saved ? `${url}/${saved.jobId}?projectId=${encodeURIComponent(projectId)}` : url,
      {
        method: saved ? "GET" : "POST",

        headers: {
          ...buildCloudAgentHeaders(true),
          "Content-Type":
            "application/json",
          "Accept":
            "application/json",
          ...(API_KEY
            ? { "X-API-Key": API_KEY }
            : {}),
        },

        body: saved ? undefined : JSON.stringify({
          projectId,
          prompt:
            cleanedPrompt,
          history: history.slice(-10).map((turn) => ({
            role: turn.role,
            content: turn.content.slice(0, 2000),
          })),
        }),
      }
    );

    onProgress?.("Preparing request", response.headers.get("X-Request-ID") || "");
    if (!response.ok) {
      if (saved && response.status === 404) clearPendingBuild(projectId);
      const message =
        await getErrorMessage(response);

      throw new Error(message);
    }

    let job = await response.json();
    if (job.jobId) savePendingBuild(projectId, { jobId: job.jobId, prompt: job.prompt || cleanedPrompt, startedAt: saved?.startedAt || job.createdAt || Date.now() });
    const deadline = (saved?.startedAt || job.createdAt || Date.now()) + 3600000;
    while (job.state === "running") {
      onProgress?.(job.stage || "Working on your request", job.requestId || "");
      if (Date.now() > deadline) { clearPendingBuild(projectId); throw new Error('This background request has expired. Please reconnect to your project before retrying.'); }
      await new Promise(resolve => setTimeout(resolve, 1500));
      if (document.hidden || !navigator.onLine) {
        onProgress?.('Build continues on the server. Reconnecting when you return…', job.requestId || '');
        continue;
      }
      let poll: Response | undefined;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          poll = await fetch(`${CLOUD_AGENT_URL}/agent/jobs/${job.jobId}?projectId=${encodeURIComponent(projectId)}`, {
            headers: buildCloudAgentHeaders(), signal: AbortSignal.timeout(20000),
          });
          if (poll.status < 500 || attempt === 2) break;
        } catch { /* A paused phone or temporary disconnection does not cancel the server job. */ }
        onProgress?.("Reconnecting to request", job.requestId || "");
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
      if (!poll || poll.status >= 500) { onProgress?.('Build continues in the background. Reconnecting…', job.requestId || ''); continue; }
      if (poll.status === 404) clearPendingBuild(projectId);
      if (!poll.ok) throw new Error(await getErrorMessage(poll));
      job = await poll.json();
    }
    onProgress?.(job.stage || "Complete", job.requestId || "");
    if (job.jobId) markBuildHandled(projectId, job.jobId);
    const data = job.result;
    if (!data || data.status !== "success") {
      const error = Object.assign(new Error(data?.message || "The request failed. Please retry or report this problem."), {
        previousPreviewUrl: data?.previousPreviewPreserved ? data.previewUrl : null,
      });
      throw error;
    }

    return {
      requestType: data.requestType === "chat" ? "chat" : "build",
      text:
        typeof data.text ===
        "string"
          ? data.text
          : typeof data.answer === "string"
            ? data.answer
            : "GeneSys completed the request.",

      agent:
        typeof data.agent ===
        "string"
          ? data.agent
          : "GeneSys Agent",

      steps:
        Array.isArray(data.steps)
          ? data.steps
          : [],

      modifiedFiles:
        Array.isArray(
          data.modifiedFiles
        )
          ? data.modifiedFiles
          : [],

      buildAttempted:
        data.buildAttempted === true,

      buildPassed:
        data.buildPassed === true,

      browserVerified:
        data.browserVerified === true,

      checkpointId:
        typeof data.checkpoint?.checkpointId === "string"
          ? data.checkpoint.checkpointId
          : null,

      checkpointStatus:
        typeof data.checkpoint?.status === "string"
          ? data.checkpoint.status
          : null,

      promotionToken:
        typeof data.promotionToken === "string"
          ? data.promotionToken
          : null,

      previewUrl:
        typeof data.previewUrl === "string"
          ? data.previewUrl
          : null,

      previewStarted:
        data.previewStarted === true,

      status:
        typeof data.status ===
        "string"
          ? data.status
          : "success",
    };
  } catch (error) {
    if (
      error instanceof TypeError
    ) {
      throw new Error(
        `Unable to reach the GeneSys agent at ${url}. ` +
        `Make sure the backend is running and accessible from this browser.`
      );
    }

    throw error;
  }
}

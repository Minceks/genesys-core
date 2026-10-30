import { readVerificationReport, type VerificationReportData } from '../components/genesys/verification-report';
import { apiFetch } from '../lib/api';
import { runAgentJob } from '../lib/agent-job';
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
  checkpoint?: { status?: string; checkpointId?: string };
  promotionToken?: string;
  verification?: VerificationReportData;
  metrics?: { durationSeconds: number; modelResponses: number; reportedTokens: number; filesChanged: number };
  browserVerified?: boolean;
  previewUrl?: string | null;
  mode?: 'build' | 'plan' | 'discuss';
  proposedBuildPrompt?: string | null;
  text: string;
  agent: string;
  steps: AgentStep[];
  modifiedFiles: string[];
  buildAttempted: boolean;
  buildPassed: boolean;
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
  projectId: string,
  options: { mode?: 'build' | 'plan' | 'discuss'; history?: { role: 'user' | 'assistant'; content: string }[]; onProgress?: (stage: string) => void } = {},
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
    const data = await runAgentJob(projectId, cleanedPrompt, options);

    return {
      checkpoint: data.checkpoint && typeof data.checkpoint.checkpointId === 'string' ? data.checkpoint : undefined,
      promotionToken: typeof data.promotionToken === 'string' ? data.promotionToken : undefined,
      verification: readVerificationReport(data.verification),
      metrics: data.metrics && typeof data.metrics.durationSeconds === 'number' ? data.metrics : undefined,
      browserVerified: data.browserVerified === true,
      previewUrl: typeof data.previewUrl === 'string' && data.previewUrl.startsWith('https://') ? data.previewUrl : null,
      mode: ['build', 'plan', 'discuss'].includes(data.mode) ? data.mode : undefined,
      proposedBuildPrompt: typeof data.proposedBuildPrompt === 'string' ? data.proposedBuildPrompt : null,
      text:
        typeof data.message === 'string' && data.status === 'error' ? data.message : typeof data.text === 'string' ? data.text : typeof data.answer ===
        "string"
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

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
  prompt: string
): Promise<GenesysAgentResponse> {
  const cleanedPrompt = prompt.trim();

  if (!cleanedPrompt) {
    throw new Error(
      "GeneSys request cannot be empty."
    );
  }

  const url =
    `${CLOUD_AGENT_URL}/agent/run`;

  try {
    const response = await fetch(
      url,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
          "Accept":
            "application/json",
          ...(API_KEY
            ? { "X-API-Key": API_KEY }
            : {}),
        },

        body: JSON.stringify({
          projectId:
            "genesys-project",
          prompt:
            cleanedPrompt,
        }),
      }
    );

    if (!response.ok) {
      const message =
        await getErrorMessage(response);

      throw new Error(message);
    }

    const data =
      await response.json();

    return {
      text:
        typeof data.answer ===
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
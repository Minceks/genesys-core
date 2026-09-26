import { Groq } from "groq-sdk";

const apiKey = import.meta.env.VITE_GROQ_API_KEY;

if (!apiKey) {
  console.warn("VITE_GROQ_API_KEY is not configured.");
}

const groq = new Groq({
  apiKey,
  dangerouslyAllowBrowser: true,
});

const CLOUD_AGENT_URL =
  "https://remarkable-generosity-production-7d5a.up.railway.app";

const MODELS = {
  architect: "openai/gpt-oss-120b",
  builder: "qwen/qwen3.8-27b",
  reviewer: "openai/gpt-oss-20b",
} as const;

type GeneratedFile = {
  path: string;
  content: string;
};

type BuildResult = {
  summary: string;
  previewHtml: string;
  files: GeneratedFile[];
};

function parseJson<T>(raw: string): T {
  try {
    return JSON.parse(raw);
  } catch {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}");

    if (start !== -1 && end !== -1 && end > start) {
      return JSON.parse(raw.slice(start, end + 1));
    }

    throw new Error("AI returned invalid JSON.");
  }
}

async function callAgent(
  model: string,
  systemPrompt: string,
  userPrompt: string,
  maxTokens = 24000
) {
  const completion = await groq.chat.completions.create({
    model,
    messages: [
      {
        role: "system",
        content: systemPrompt,
      },
      {
        role: "user",
        content: userPrompt,
      },
    ],
    temperature: 0.4,
    max_completion_tokens: maxTokens,
    response_format: {
      type: "json_object",
    },
  });

  const content =
    completion.choices[0]?.message?.content || "";

  if (!content) {
    throw new Error(`${model} returned an empty response.`);
  }

  return content;
}

/**
 * Get lightweight project context from Railway.
 */
async function getProjectContext() {
  try {
    const [treeResponse, roadmapResponse] =
      await Promise.all([
        fetch(`${CLOUD_AGENT_URL}/list-files`),

        fetch(`${CLOUD_AGENT_URL}/read-file`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            filename: "roadmap.md",
          }),
        }),
      ]);

    const treeData = treeResponse.ok
      ? await treeResponse.json()
      : { tree: {} };

    const roadmapData = roadmapResponse.ok
      ? await roadmapResponse.json()
      : { content: "" };

    return {
      tree: treeData.tree || {},
      roadmap:
        roadmapData.content ||
        "No roadmap available.",
    };
  } catch (error) {
    console.warn(
      "Cloud project context unavailable:",
      error
    );

    return {
      tree: {},
      roadmap: "No roadmap available.",
    };
  }
}

/**
 * MAIN AGENT PIPELINE
 *
 * 1. Architect
 * 2. Builder
 * 3. Reviewer / Polish
 */
export async function askGenesys(prompt: string) {
  const context = await getProjectContext();

  // =========================================================
  // STAGE 1 — ARCHITECT
  // =========================================================

  const architectureRaw = await callAgent(
    MODELS.architect,

    `
You are GENESYS LEAD ARCHITECT.

Your job is to understand the user's request and design a
production-quality implementation plan.

Do NOT write the final code yet.

Think about:
- product purpose
- UX
- visual design
- interactions
- state
- edge cases
- responsiveness
- accessibility
- file architecture
- technical requirements
- acceptance criteria

For games:
- the game must actually be playable
- keyboard controls must work
- touch/mobile controls should work where appropriate
- score/state/game-over/restart behavior must work
- no fake buttons
- no placeholder interactions

For dashboards/apps:
- buttons must perform real actions
- forms must actually update state
- navigation must work
- no decorative controls pretending to work

Return JSON ONLY:

{
  "productGoal": "...",
  "experience": "...",
  "architecture": ["..."],
  "acceptanceCriteria": ["..."],
  "filesNeeded": ["..."],
  "previewRequirements": ["..."]
}
`,

    JSON.stringify({
      userRequest: prompt,
      currentProject: context.tree,
      roadmap: context.roadmap,
    }),

    12000
  );

  const architecture = parseJson<{
    productGoal: string;
    experience: string;
    architecture: string[];
    acceptanceCriteria: string[];
    filesNeeded: string[];
    previewRequirements: string[];
  }>(architectureRaw);

  // =========================================================
  // STAGE 2 — BUILDER
  // =========================================================

  const builderRaw = await callAgent(
    MODELS.builder,

    `
You are GENESYS SENIOR PRODUCT ENGINEER.

Build the product described by the user.

The output will be executed by a real application.
It is NOT a mockup.

QUALITY BAR:
- polished visual hierarchy
- professional spacing
- responsive layout
- smooth interactions
- complete functionality
- useful empty/error states
- no fake buttons
- no TODO placeholders
- no "coming soon"
- no unfinished sections
- no lorem ipsum

FOR GAMES:
The preview must be genuinely playable.
Implement real game logic, not a visual imitation.

Example expectations when relevant:
- keyboard input
- touch input
- collision detection
- score
- high score
- pause
- restart
- game over
- difficulty progression
- visual feedback
- responsive gameplay area

PREVIEW:
Create a COMPLETE standalone HTML document.

The preview:
- must work inside an iframe
- must use vanilla JavaScript
- must not require React
- must not require npm
- should avoid external dependencies
- must contain all CSS/JS needed for the experience
- must be directly interactive

PRODUCTION FILES:
Create real production files for the project.
Use React/TSX where appropriate.
Use the existing project conventions.
Every file must contain its COMPLETE contents.

IMPORTANT:
Return JSON ONLY.

{
  "summary": "...",
  "previewHtml": "<!DOCTYPE html>...",
  "files": [
    {
      "path": "src/...",
      "content": "complete file..."
    }
  ]
}
`,

    JSON.stringify({
      userRequest: prompt,
      architecture,
      currentProject: context.tree,
      roadmap: context.roadmap,
    }),

    32000
  );

  const draft = parseJson<BuildResult>(builderRaw);

  // =========================================================
  // STAGE 3 — QA / POLISH
  // =========================================================

  let finalBuild = draft;

  try {
    const reviewerRaw = await callAgent(
      MODELS.reviewer,

      `
You are GENESYS QA + POLISH ENGINEER.

You are reviewing a generated product before it reaches the user.

Your job is NOT to merely comment on the code.

Your job is to FIX IT.

Check:
- functionality
- missing event handlers
- broken state
- broken buttons
- impossible interactions
- mobile behavior
- keyboard behavior
- game mechanics
- layout problems
- obvious runtime errors
- incomplete UI
- placeholders
- weak visual hierarchy
- accessibility issues
- empty states
- restart/error behavior

For a game, mentally walk through:
1. Start
2. Player input
3. Movement
4. Collision
5. Score
6. Difficulty
7. Game over
8. Restart
9. Mobile/touch behavior

If something is wrong, modify the code.

Return the COMPLETE corrected product.

Return JSON ONLY:

{
  "summary": "...",
  "previewHtml": "<!DOCTYPE html>...",
  "files": [
    {
      "path": "src/...",
      "content": "complete corrected file..."
    }
  ]
}
`,

      JSON.stringify({
        userRequest: prompt,
        acceptanceCriteria:
          architecture.acceptanceCriteria,
        draft,
      }),

      32000
    );

    finalBuild = parseJson<BuildResult>(
      reviewerRaw
    );
  } catch (error) {
    console.warn(
      "Reviewer failed. Using builder result:",
      error
    );
  }

  // =========================================================
  // RETURN A STABLE FORMAT TO build.tsx
  // =========================================================

  let text = "";

  text += "<GENESYS_PREVIEW>\n";
  text += finalBuild.previewHtml.trim();
  text += "\n</GENESYS_PREVIEW>\n\n";

  for (const file of finalBuild.files) {
    text += `---FILE: ${file.path}---\n`;
    text += "[CODE START]\n";
    text += file.content;
    text += "\n[CODE END]\n\n";
  }

  text += finalBuild.summary;

  return {
    text,
    agent: "Genesys Build Council",
  };
}

/**
 * Write a generated file through Railway -> GitHub.
 */
export async function writeFileToGitHub(
  projectId: string,
  filename: string,
  code: string
) {
  const response = await fetch(
    `${CLOUD_AGENT_URL}/write-file`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        projectId,
        filename,
        code,
      }),
    }
  );

  const result = await response.json();

  if (!response.ok) {
    throw new Error(
      result.message ||
        "Failed to write file to GitHub"
    );
  }

  return result;
}

/**
 * Health check.
 */
export async function checkCloudAgent() {
  const response = await fetch(
    `${CLOUD_AGENT_URL}/health`
  );

  if (!response.ok) {
    throw new Error("Cloud Agent is offline.");
  }

  return response.json();
}
import { createRoute } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import { Navbar } from "@/components/genesys/navbar";
import { askGenesys } from "@/utils/ai.functions";

import {
  Send,
  Brain,
  ListChecks,
  Loader2,
  Eye,
  FileCode,
  RefreshCw,
  Check,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_KEY = (
  import.meta.env.VITE_CLOUD_AGENT_API_KEY || ""
).trim();


// ============================================================
// CONFIG
// ============================================================

const CLOUD_AGENT_URL = (
  import.meta.env.VITE_CLOUD_AGENT_URL ||
  (import.meta.env.DEV
    ? "http://127.0.0.1:5000"
    : "https://remarkable-generosity-production-7d5a.up.railway.app")
).replace(/\/+$/, "");

const LOCAL_PREVIEW_URL = "http://127.0.0.1:4173";


// ============================================================
// TYPES
// ============================================================

type ProjectTree = {
  routes: string[];
  components: string[];
};

type AgentStep = {
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

type AgentResponse = {
  text: string;
  agent?: string;
  steps?: AgentStep[];
  modifiedFiles?: string[];
  buildAttempted?: boolean;
  buildPassed?: boolean;
  status?: string;
};

type ChatMessage = {
  role: "user" | "bot";
  text: string;
  agent?: string;
  thought?: string;
  plan?: string;
  hasFile?: boolean;
  modifiedFiles?: string[];
  buildPassed?: boolean;
};


// ============================================================
// HELPERS
// ============================================================

function cleanAgentText(text: string): string {
  return text
    .replace(
      /<THOUGHT>[\s\S]*?<\/THOUGHT>/gi,
      ""
    )
    .replace(
      /<PLAN>[\s\S]*?<\/PLAN>/gi,
      ""
    )
    .replace(
      /<GENESYS_PREVIEW>[\s\S]*?(?:<\/GENESYS_PREVIEW>|$)/gi,
      ""
    )
    .replace(
      /---FILE:[\s\S]*?\[CODE END\]/gi,
      ""
    )
    .trim();
}

function extractLegacyTag(
  text: string,
  tag: string
): string | undefined {
  const match = text.match(
    new RegExp(
      `<${tag}>([\\s\\S]*?)<\\/${tag}>`,
      "i"
    )
  );

  return match?.[1]?.trim() || undefined;
}


// ============================================================
// PAGE
// ============================================================

function BuildPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [previewUrl, setPreviewUrl] = useState(
    LOCAL_PREVIEW_URL
  );

  const [previewKey, setPreviewKey] = useState(0);

  const [previewOnline, setPreviewOnline] =
    useState(false);

  const [projectTree, setProjectTree] =
    useState<ProjectTree>({
      routes: [],
      components: [],
    });

  const [messages, setMessages] =
    useState<ChatMessage[]>(() => {
      if (typeof window === "undefined") {
        return [];
      }

      try {
        const saved =
          sessionStorage.getItem("genesys_v3");

        return saved
          ? JSON.parse(saved)
          : [];
      } catch {
        return [];
      }
    });

  const scrollRef =
    useRef<HTMLDivElement>(null);


  // ==========================================================
  // PROJECT EXPLORER
  // ==========================================================

  async function refreshFiles() {
    try {
      const response = await fetch(
        `${CLOUD_AGENT_URL}/list-files`,
        {
          headers: {
            ...(API_KEY
              ? { "X-API-Key": API_KEY }
              : {}),
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Explorer request failed: ${response.status}`
        );
      }

      const data =
        await response.json();

      if (data.tree) {
        setProjectTree({
          routes: Array.isArray(
            data.tree.routes
          )
            ? data.tree.routes
            : [],

          components:
            Array.isArray(
              data.tree.components
            )
              ? data.tree.components
              : [],
        });
      }
    } catch (error) {
      console.error(
        "GeneSys project explorer unavailable:",
        error
      );
    }
  }


  // ==========================================================
  // PREVIEW HEALTH CHECK
  // ==========================================================

  async function checkPreview() {
    try {
      const response = await fetch(
        previewUrl,
        {
          method: "GET",
          cache: "no-store",
        }
      );

      setPreviewOnline(
        response.ok
      );
    } catch {
      setPreviewOnline(false);
    }
  }


  // ==========================================================
  // INITIALIZATION
  // ==========================================================

  useEffect(() => {
    void refreshFiles();
  }, []);

  useEffect(() => {
    void checkPreview();

    const interval = window.setInterval(
      () => {
        void checkPreview();
      },
      5000
    );

    return () => {
      window.clearInterval(interval);
    };
  }, [previewUrl]);

  useEffect(() => {
    try {
      sessionStorage.setItem(
        "genesys_v3",
        JSON.stringify(messages)
      );
    } catch {
      // Ignore storage failures.
    }

    if (scrollRef.current) {
      scrollRef.current.scrollTop =
        scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);


  // ==========================================================
  // SEND AGENT REQUEST
  // ==========================================================

  async function handleSend(
    overridePrompt?: string
  ) {
    const promptText = (
      overridePrompt ?? input
    ).trim();

    if (!promptText || loading) {
      return;
    }

    setLoading(true);

    // Add user message only for normal chat sends.
    if (!overridePrompt) {
      setMessages((previous) => [
        ...previous,
        {
          role: "user",
          text: promptText,
        },
      ]);

      setInput("");
    }

    try {
      // ------------------------------------------------------
      // RUN REAL SERVER-SIDE AGENT
      // ------------------------------------------------------

      const response =
        (await askGenesys(
          promptText
        )) as AgentResponse;

      const text =
        response.text ||
        "GeneSys completed the request.";

      const steps =
        response.steps || [];

      // ------------------------------------------------------
      // FIND PREVIEW SERVER RESULT
      // ------------------------------------------------------

      const previewStep =
        steps.find(
          (step) =>
            step.tool ===
              "start_preview" &&
            step.status === "success" &&
            typeof step.result?.url ===
              "string" &&
            step.result.url.length > 0
        );

      if (
        previewStep?.result?.url
      ) {
        const nextPreviewUrl =
          previewStep.result.url;

        setPreviewUrl(
          nextPreviewUrl
        );

        // Force iframe reload after
        // a new agent execution.
        setPreviewKey(
          (value) => value + 1
        );
      } else if (
        response.buildPassed ||
        steps.some(
          (step) =>
            step.tool ===
              "run_build" &&
            step.status === "success" &&
            step.result?.success === true
        )
      ) {
        // Even when the preview server
        // is already running, reload the
        // iframe after a successful build.
        setPreviewKey(
          (value) => value + 1
        );
      }

      // ------------------------------------------------------
      // COUNT FILE CHANGES
      // ------------------------------------------------------

      const writtenFiles =
        response.modifiedFiles ||
        steps
          .filter(
            (step) =>
              step.tool ===
                "write_file" &&
              step.status ===
                "success"
          )
          .map(
            (step) =>
              step.result?.file
          )
          .filter(
            (
              file
            ): file is string =>
              typeof file ===
              "string"
          );

      const uniqueFiles =
        [...new Set(writtenFiles)];

      // ------------------------------------------------------
      // REFRESH EXPLORER
      // ------------------------------------------------------

      if (uniqueFiles.length > 0) {
        await refreshFiles();
      }

      // ------------------------------------------------------
      // LEGACY THINKING / PLAN EXTRACTION
      // ------------------------------------------------------

      const thought =
        extractLegacyTag(
          text,
          "THOUGHT"
        );

      const plan =
        extractLegacyTag(
          text,
          "PLAN"
        );

      const cleanDisplay =
        cleanAgentText(text);

      // ------------------------------------------------------
      // ADD ASSISTANT MESSAGE
      // ------------------------------------------------------

      setMessages((previous) => [
        ...previous,
        {
          role: "bot",
          text:
            cleanDisplay ||
            "GeneSys completed the requested change.",

          thought,

          plan,

          agent:
            response.agent ||
            "GeneSys Agent",

          hasFile:
            uniqueFiles.length > 0,

          modifiedFiles:
            uniqueFiles,

          buildPassed:
            response.buildPassed ||
            steps.some(
              (step) =>
                step.tool ===
                  "run_build" &&
                step.status ===
                  "success" &&
                step.result?.success ===
                  true
            ),
        },
      ]);
    } catch (error) {
      console.error(
        "GeneSys system error:",
        error
      );

      const message =
        error instanceof Error
          ? error.message
          : String(error);

      setMessages((previous) => [
        ...previous,
        {
          role: "bot",
          text:
            `❌ Connection Error: ${message}`,
          agent: "System",
        },
      ]);
    } finally {
      setLoading(false);

      // Re-check the preview after
      // the agent has finished.
      window.setTimeout(
        () => {
          void checkPreview();
        },
        500
      );
    }
  }


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="flex flex-col h-screen bg-[#020202] text-white overflow-hidden font-sans">
      <Navbar />

      <div className="flex flex-1 pt-16 overflow-hidden">

        {/* ================================================== */}
        {/* COLUMN 1 — PROJECT EXPLORER                       */}
        {/* ================================================== */}

        <aside className="w-56 shrink-0 border-r border-white/5 bg-zinc-950/80 p-4 hidden md:flex flex-col overflow-y-auto">

          <div className="flex items-center justify-between mb-6 opacity-60">
            <span className="text-[9px] font-black uppercase tracking-[0.3em]">
              Project Explorer
            </span>

            <RefreshCw
              size={12}
              onClick={() => {
                void refreshFiles();
              }}
              className="cursor-pointer hover:rotate-180 transition-all"
            />
          </div>


          <div className="space-y-6">

            {/* ROUTES */}

            <div>
              <div className="flex items-center gap-2 mb-2">
                <ListChecks
                  size={11}
                  className="text-blue-400/70"
                />

                <h4 className="text-[8px] font-bold text-blue-400/50 uppercase tracking-widest">
                  Routes
                </h4>
              </div>

              {projectTree.routes.length >
              0 ? (
                <div className="space-y-1">
                  {projectTree.routes.map(
                    (file) => (
                      <div
                        key={file}
                        className="text-[10px] text-white/35 p-1.5 rounded font-mono flex items-center gap-2 hover:bg-white/5 hover:text-white/70 transition-colors"
                        title={file}
                      >
                        <FileCode
                          size={10}
                          className="shrink-0"
                        />

                        <span className="truncate">
                          {file}
                        </span>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="text-[9px] text-white/15 px-2">
                  No routes found
                </div>
              )}
            </div>


            {/* COMPONENTS */}

            <div>
              <div className="flex items-center gap-2 mb-2">
                <Brain
                  size={11}
                  className="text-purple-400/70"
                />

                <h4 className="text-[8px] font-bold text-purple-400/50 uppercase tracking-widest">
                  Components
                </h4>
              </div>

              {projectTree.components.length >
              0 ? (
                <div className="space-y-1">
                  {projectTree.components.map(
                    (file) => (
                      <div
                        key={file}
                        className="text-[10px] text-white/35 p-1.5 rounded font-mono flex items-center gap-2 hover:bg-white/5 hover:text-white/70 transition-colors"
                        title={file}
                      >
                        <FileCode
                          size={10}
                          className="shrink-0"
                        />

                        <span className="truncate">
                          {file}
                        </span>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="text-[9px] text-white/15 px-2">
                  No components found
                </div>
              )}
            </div>

          </div>
        </aside>


        {/* ================================================== */}
        {/* COLUMN 2 — CHAT                                  */}
        {/* ================================================== */}

        <aside className="w-[420px] shrink-0 border-r border-white/5 flex flex-col bg-zinc-950/40 backdrop-blur-xl">

          {/* CHAT HISTORY */}

          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-6"
          >

            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-8">
                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/10 flex items-center justify-center mb-4">
                  <Brain
                    size={22}
                    className="text-blue-400/60"
                  />
                </div>

                <h3 className="text-sm font-semibold text-white/70 mb-2">
                  GeneSys Agent
                </h3>

                <p className="text-[11px] leading-relaxed text-white/25">
                  Describe what you want to
                  build. GeneSys will inspect
                  the project, edit the real
                  files, build the application,
                  repair errors, and launch the
                  live preview.
                </p>
              </div>
            )}

            {messages.map(
              (message, index) => (
                <div
                  key={index}
                  className={`flex flex-col ${
                    message.role === "user"
                      ? "items-end"
                      : "items-start"
                  }`}
                >

                  {/* AGENT LABEL */}

                  {message.agent && (
                    <div className="text-[9px] font-bold text-blue-400/50 uppercase tracking-widest mb-2">
                      {message.agent}
                    </div>
                  )}


                  {/* THOUGHT */}

                  {message.thought && (
                    <div className="mb-2 p-3 bg-blue-500/5 border border-blue-500/10 rounded-xl text-[10px] text-blue-300 italic w-full leading-relaxed">
                      💭 {message.thought}
                    </div>
                  )}


                  {/* PLAN */}

                  {message.plan && (
                    <div className="mb-2 p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-xl text-[10px] text-emerald-400 w-full">
                      <ReactMarkdown>
                        {message.plan}
                      </ReactMarkdown>
                    </div>
                  )}


                  {/* MESSAGE */}

                  <div
                    className={`p-4 rounded-2xl text-sm max-w-full ${
                      message.role === "user"
                        ? "bg-blue-600 shadow-xl shadow-blue-900/20"
                        : "bg-zinc-900 border border-white/5"
                    }`}
                  >
                    <ReactMarkdown
                      remarkPlugins={[
                        remarkGfm,
                      ]}
                    >
                      {message.text}
                    </ReactMarkdown>
                  </div>


                  {/* FILES */}

                  {message.role ===
                    "bot" &&
                    message.hasFile && (
                      <div className="mt-2 space-y-1">

                        <div className="flex items-center gap-1 text-[8px] font-black text-green-500/60 bg-green-500/5 px-2 py-1 rounded-full border border-green-500/10 uppercase tracking-widest">
                          <Check size={8} />

                          {
                            message
                              .modifiedFiles
                              ?.length
                          }

                          {" "}
                          file
                          {
                            message
                              .modifiedFiles
                              ?.length === 1
                              ? ""
                              : "s"
                          }
                          {" "}
                          updated
                        </div>

                        {message.modifiedFiles
                          ?.slice(0, 6)
                          .map(
                            (file) => (
                              <div
                                key={file}
                                className="text-[9px] text-white/25 font-mono px-2"
                              >
                                • {file}
                              </div>
                            )
                          )}

                      </div>
                    )}


                  {/* BUILD STATUS */}

                  {message.role ===
                    "bot" &&
                    message.buildPassed && (
                      <div className="flex items-center gap-1 mt-2 text-[8px] font-black text-emerald-400/60 bg-emerald-500/5 px-2 py-1 rounded-full border border-emerald-500/10 uppercase tracking-widest">
                        <Check size={8} />
                        Build verified
                      </div>
                    )}

                </div>
              )
            )}


            {/* LOADING */}

            {loading && (
              <div className="flex items-start">
                <div className="bg-zinc-900 border border-white/5 rounded-2xl p-4 flex items-center gap-3">

                  <Loader2
                    size={16}
                    className="animate-spin text-blue-400"
                  />

                  <div>
                    <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest">
                      GeneSys is working
                    </div>

                    <div className="text-[9px] text-white/25 mt-1">
                      Inspecting → Editing →
                      Building → Verifying
                    </div>
                  </div>

                </div>
              </div>
            )}

          </div>


          {/* INPUT */}

          <div className="p-4 bg-black/40 border-t border-white/5">

            <div className="flex items-end gap-2 bg-zinc-900 border border-white/10 rounded-2xl p-2">

              <textarea
                value={input}
                onChange={(event) =>
                  setInput(event.target.value)
                }
                onKeyDown={(event) => {
                  if (
                    event.key ===
                      "Enter" &&
                    !event.shiftKey
                  ) {
                    event.preventDefault();
                    void handleSend();
                  }
                }}
                placeholder="Describe what you want to build..."
                className="flex-1 bg-transparent border-none outline-none text-sm p-2 resize-none max-h-32 text-white placeholder:text-white/20"
                rows={1}
                disabled={loading}
              />

              <button
                onClick={() => {
                  void handleSend();
                }}
                disabled={
                  loading ||
                  !input.trim()
                }
                className="bg-blue-600 p-2.5 rounded-xl shadow-lg hover:bg-blue-500 disabled:opacity-30 disabled:hover:bg-blue-600 transition-all"
                aria-label="Send request"
              >
                {loading ? (
                  <Loader2
                    size={18}
                    className="animate-spin"
                  />
                ) : (
                  <Send size={18} />
                )}
              </button>

            </div>

            <div className="text-[8px] text-white/15 mt-2 px-2">
              Enter to send · Shift + Enter
              for a new line
            </div>

          </div>
        </aside>


        {/* ================================================== */}
        {/* COLUMN 3 — LIVE PREVIEW                           */}
        {/* ================================================== */}

        <main className="flex-1 p-6 relative min-w-0">

          <div className="w-full h-full rounded-[2.5rem] overflow-hidden border border-white/5 bg-black shadow-2xl relative">

            {/* PREVIEW HEADER */}

            <div className="absolute top-0 left-0 right-0 z-20 h-12 px-5 flex items-center justify-between bg-black/60 backdrop-blur-xl border-b border-white/5">

              <div className="flex items-center gap-3">

                <div className="flex items-center gap-2">
                  <Eye
                    size={13}
                    className="text-blue-400"
                  />

                  <span className="text-[9px] font-black uppercase tracking-[0.25em] text-white/50">
                    Live Preview
                  </span>
                </div>


                <div className="flex items-center gap-1.5">

                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      previewOnline
                        ? "bg-emerald-400"
                        : "bg-red-400"
                    }`}
                  />

                  <span className="text-[8px] uppercase tracking-widest text-white/25">
                    {previewOnline
                      ? "Online"
                      : "Offline"}
                  </span>

                </div>

              </div>


              <div className="flex items-center gap-2">

                <button
                  type="button"
                  onClick={() => {
                    setPreviewKey(
                      (value) =>
                        value + 1
                    );

                    void checkPreview();
                  }}
                  className="p-2 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
                  title="Refresh preview"
                >
                  <RefreshCw
                    size={13}
                  />
                </button>


                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 rounded-lg text-white/30 hover:text-white/70 hover:bg-white/5 transition-colors"
                  title="Open preview in new tab"
                >
                  <ExternalLink
                    size={13}
                  />
                </a>

              </div>
            </div>


            {/* PREVIEW */}

            {previewUrl ? (
              <iframe
                key={previewKey}
                src={previewUrl}
                title="GeneSys Application Preview"
                className="absolute inset-0 pt-12 w-full h-full border-0 bg-black"
                allow="fullscreen"
                sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">

                  <AlertCircle
                    size={24}
                    className="mx-auto mb-3 text-white/10"
                  />

                  <p className="text-[10px] text-white/20 uppercase tracking-[0.25em]">
                    Preview unavailable
                  </p>

                </div>
              </div>
            )}


            {/* INITIAL OVERLAY */}

            {!previewOnline &&
              !loading && (
                <div className="absolute inset-0 z-10 pointer-events-none flex items-center justify-center pt-12">
                  <div className="bg-black/70 backdrop-blur-md border border-white/5 rounded-2xl px-5 py-4 text-center">

                    <div className="flex items-center justify-center gap-2 mb-2">
                      <AlertCircle
                        size={14}
                        className="text-white/30"
                      />

                      <span className="text-[9px] font-black uppercase tracking-widest text-white/40">
                        Waiting for preview
                      </span>
                    </div>

                    <p className="text-[9px] text-white/20">
                      Start the application preview
                      through the GeneSys agent.
                    </p>

                  </div>
                </div>
              )}


            {/* WORKING OVERLAY */}

            {loading && (
              <div className="absolute top-16 right-5 z-30">

                <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-blue-500/10 border border-blue-500/20 backdrop-blur-xl">

                  <Loader2
                    size={12}
                    className="animate-spin text-blue-400"
                  />

                  <span className="text-[8px] font-black uppercase tracking-widest text-blue-300/70">
                    Updating application
                  </span>

                </div>

              </div>
            )}

          </div>

        </main>

      </div>
    </div>
  );
}


// ============================================================
// ROUTE
// ============================================================

export const Route = createRoute({
  getParentRoute: () =>
    rootRoute,

  path: "/build",

  component: BuildPage,
});
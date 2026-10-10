import { supabase } from '../lib/supabase';
import { createRoute, Navigate } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import { AppShell } from "@/components/AppShell";
import {
  askGenesys,
  buildCloudAgentHeaders,
  CLOUD_AGENT_URL,
} from "@/utils/ai.functions";

import {
  Send,
  ArrowRight,
  Brain,
  Loader2,
  Check,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  FileCode,
} from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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

type ChatMessage = {
  role: "user" | "bot";
  text: string;
  agent?: string;
  thought?: string;
  plan?: string;
  hasFile?: boolean;
  modifiedFiles?: string[];
  buildAttempted?: boolean;
  buildPassed?: boolean;
  browserVerified?: boolean;
  checkpointStatus?: string;
  checkpointId?: string;
  promotionToken?: string;
  promotionUrl?: string;
  promotionError?: string;
  steps?: AgentStep[];
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
      /<GENESYS_PREVIEW>[\s\S]*?<\/GENESYS_PREVIEW>/gi,
      ""
    )
    .replace(
      /---FILE:[\s\S]*?\[CODE START\][\s\S]*?\[CODE END\]/gi,
      ""
    )
    .trim();
}

function extractLegacyTag(
  text: string,
  tag: string
): string | undefined {
  const expression = new RegExp(
    `<${tag}>([\\s\\S]*?)<\\/${tag}>`,
    "i"
  );

  const match = text.match(expression);

  return match?.[1]?.trim() || undefined;
}

function extractPreviewCode(
  text: string
): string | undefined {
  const match = text.match(
    /<GENESYS_PREVIEW>([\s\S]*?)<\/GENESYS_PREVIEW>/i
  );

  return match?.[1]?.trim() || undefined;
}

function extractFiles(
  text: string
): Array<{
  filename: string;
  code: string;
}> {
  const files: Array<{
    filename: string;
    code: string;
  }> = [];

  const regex =
    /---FILE:\s*([^\r\n]+?)\s*---\s*\[CODE START\]([\s\S]*?)\[CODE END\]/gi;

  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const filename = match[1].trim();
    const code = match[2].trim();

    if (filename && code) {
      files.push({
        filename,
        code,
      });
    }
  }

  return files;
}

// ============================================================
// PAGE
// ============================================================

function BuildPage({ projectId, projectName, onProjects }: { projectId: string; projectName: string; onProjects: () => void }) {
  const chatStorageKey = `genesys_chat_${projectId}`;
  const [progressStage, setProgressStage] = useState("Preparing request");
  const [lastRequestId, setLastRequestId] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const [previewRefreshing, setPreviewRefreshing] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [failedPrompt, setFailedPrompt] = useState("");
  const [restoring, setRestoring] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportText, setReportText] = useState("");
  const [reportStatus, setReportStatus] = useState("");
  const [reportSending, setReportSending] = useState(false);
  // ----------------------------------------------------------
  // STATE
  // ----------------------------------------------------------

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);
  const [promotingCheckpoint, setPromotingCheckpoint] = useState("");

  const [previewCode, setPreviewCode] = useState("");

  const [previewUrl, setPreviewUrl] = useState(() => {
    try { return sessionStorage.getItem(`genesys_preview_${projectId}`) || ""; } catch { return ""; }
  });

  const [previewKey, setPreviewKey] = useState(0);

  const [mobileView, setMobileView] = useState<"chat" | "preview">("chat");

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
          sessionStorage.getItem(chatStorageKey);

        const restored = saved ? JSON.parse(saved) : [];
        return Array.isArray(restored)
          ? restored.filter(message => (message.role === "user" || message.role === "bot") && typeof message.text === "string")
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
        `${CLOUD_AGENT_URL}/list-files?projectId=${encodeURIComponent(projectId)}`,
        {
          headers: buildCloudAgentHeaders(),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Explorer request failed: ${response.status}`
        );
      }

      const data = await response.json();

      const tree = data.tree || {};

      setProjectTree({
        routes: Array.isArray(tree.routes)
          ? tree.routes
          : [],

        components: Array.isArray(
          tree.components
        )
          ? tree.components
          : [],
      });
    } catch (error) {
      console.error(
        "GeneSys project explorer unavailable:",
        error
      );
    }
  }

  // ==========================================================
  // WRITE FILE TO CLOUD AGENT
  // ==========================================================

  async function writeFile(
    filename: string,
    code: string
  ) {
    const response = await fetch(
      `${CLOUD_AGENT_URL}/write-file`,
      {
        method: "POST",

        headers: {
          ...buildCloudAgentHeaders(true),
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          projectId,
          filename,
          content: code,
        }),
      }
    );

    if (!response.ok) {
      const errorText =
        await response.text();

      throw new Error(
        `Failed to write ${filename}: ${response.status} ${errorText}`
      );
    }

    return response.json().catch(() => ({}));
  }

  // ==========================================================
  // INITIALIZATION
  // ==========================================================

  useEffect(() => {
    if (messages.some(message => message.buildPassed)) void refreshFiles();
    if (previewUrl) void reloadPreview();
  }, []);

  // ==========================================================
  // SAVE CHAT
  // ==========================================================

  useEffect(() => {
    try {
      sessionStorage.setItem(
        chatStorageKey,
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
  // PREVIEW
  // ==========================================================

  useEffect(() => {
    setPreviewOnline(false);
    try { sessionStorage.setItem(`genesys_preview_${projectId}`, previewUrl); } catch { /* Storage is optional. */ }
  }, [previewCode, previewUrl]);

  async function reloadPreview() {
    if (previewRefreshing || loading) return;
    if (!previewUrl) { setPreviewKey(value => value + 1); return; }
    setPreviewRefreshing(true);
    setPreviewError("");
    try {
      const response = await fetch(`${CLOUD_AGENT_URL}/preview`, {
        method: "POST", headers: buildCloudAgentHeaders(true),
        body: JSON.stringify({ projectId }),
      });
      const data = await response.json();
      if (!response.ok || data.status !== "success" || !data.url) throw new Error(data.message || "Preview could not reconnect.");
      setPreviewOnline(false);
      setPreviewUrl(data.url);
      setPreviewKey(value => value + 1);
    } catch (error) {
      setPreviewOnline(false);
      setPreviewError(error instanceof Error ? error.message : "Preview could not reconnect.");
    } finally { setPreviewRefreshing(false); }
  }

  async function sendReport() {
    if (!reportText.trim() || reportSending) return;
    setReportSending(true);
    setReportStatus("");
    try {
      const response = await fetch(`${CLOUD_AGENT_URL}/beta/feedback`, {
        method: "POST", headers: buildCloudAgentHeaders(true),
        body: JSON.stringify({ projectId, requestId: lastRequestId, stage: progressStage, message: reportText.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Report could not be sent.");
      setReportStatus(`Report received. Reference: ${data.reportId}`);
      setReportText("");
    } catch (error) { setReportStatus(error instanceof Error ? error.message : "Report could not be sent."); }
    finally { setReportSending(false); }
  }

  useEffect(() => {
    if (!loading) return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    if (!previewUrl || loading) return;
    const timer = window.setTimeout(() => void reloadPreview(), 50 * 60 * 1000);
    return () => window.clearTimeout(timer);
  }, [previewUrl, loading]);

  function openPreview() {
    if (previewUrl) {
      window.open(
        previewUrl,
        "_blank",
        "noopener,noreferrer"
      );
      return;
    }

    if (!previewCode) {
      return;
    }

    const blob = new Blob(
      [previewCode],
      {
        type: "text/html",
      }
    );

    const url =
      URL.createObjectURL(blob);

    window.open(
      url,
      "_blank",
      "noopener,noreferrer"
    );

    window.setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 10000);
  }

  // ==========================================================
  // SEND REQUEST
  // ==========================================================

  async function handleSend(
    overridePrompt?: string
  ) {
    const promptText = (
      overridePrompt ?? input
    ).trim();

    if (!promptText || loading || restoring) {
      return;
    }

    setLoading(true);
    setFailedPrompt("");
    setProgressStage("Preparing request");
    setElapsed(0);
    setLastRequestId("");

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
      // 1. CALL RAILWAY CLOUD AGENT
      // ------------------------------------------------------

      const response =
        await askGenesys(
          promptText,
          messages
            .filter((message) => message.role === "user" || message.role === "bot")
            .slice(-10)
            .map((message) => ({
              role: message.role === "bot" ? "assistant" as const : "user" as const,
              content: message.text,
            })),
          (stage, requestId) => { setProgressStage(stage); setLastRequestId(requestId); },
          projectId,
        );

      const text = response.text || "";
      const isBuildRequest = response.requestType === "build";

      const livePreviewUrl =
        isBuildRequest && typeof response.previewUrl === "string"
          ? response.previewUrl
          : "";

      if (isBuildRequest && livePreviewUrl) {
        setPreviewUrl(livePreviewUrl);
        setPreviewCode("");
        setPreviewError("");
      }

      if (livePreviewUrl) {
        setPreviewCode("");
        setPreviewOnline(true);
        setPreviewKey((value) => value + 1);
        setMobileView("preview");
      } else if (isBuildRequest && response.previewStarted === false && !previewUrl) {
        setPreviewOnline(false);
      }

      // ------------------------------------------------------
      // 2. EXTRACT PREVIEW
      // ------------------------------------------------------

      const preview = isBuildRequest
        ? extractPreviewCode(text)
        : undefined;

      if (preview) {
        setPreviewCode(preview);
        if (!livePreviewUrl) {
          setPreviewOnline(true);
        }
      }

      // ------------------------------------------------------
      // 3. EXTRACT FILES
      // ------------------------------------------------------

      const files = isBuildRequest
        ? extractFiles(text)
        : [];

      const modifiedFiles: string[] = [...response.modifiedFiles];

      for (const file of files) {
        try {
          await writeFile(
            file.filename,
            file.code
          );

          modifiedFiles.push(
            file.filename
          );
        } catch (fileError) {
          console.error(
            `Failed to write ${file.filename}:`,
            fileError
          );
        }
      }

      // ------------------------------------------------------
      // 4. REFRESH PROJECT EXPLORER
      // ------------------------------------------------------

      if (modifiedFiles.length > 0) {
        await refreshFiles();
      }

      // ------------------------------------------------------
      // 5. EXTRACT ARCHITECTURE DATA
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
      // 6. ADD RESPONSE TO CHAT
      // ------------------------------------------------------

      setMessages((previous) => [
        ...previous,
        {
          role: "bot",

          text:
            cleanDisplay ||
            "GeneSys architectural synchronization complete.",

          agent:
            response.agent ||
            "Chief Architect",

          thought,

          plan,

          hasFile:
            modifiedFiles.length > 0,

          modifiedFiles,

          buildAttempted:
            response.buildAttempted,

          buildPassed:
            response.buildPassed,

          browserVerified:
            response.browserVerified,

          checkpointStatus:
            response.checkpointStatus || undefined,

          checkpointId:
            response.buildPassed &&
            response.browserVerified &&
            response.checkpointStatus === "success"
              ? response.checkpointId || undefined
              : undefined,

          promotionToken:
            response.buildPassed &&
            response.browserVerified &&
            response.checkpointStatus === "success"
              ? response.promotionToken || undefined
              : undefined,

          steps:
            response.steps || [
              {
                tool: "cloud_agent",
                status: "success",
              },
            ],
        },
      ]);
    } catch (error) {
      setFailedPrompt(promptText);
      const previousUrl = (error as { previousPreviewUrl?: string })?.previousPreviewUrl;
      if (previousUrl) { setPreviewUrl(previousUrl); setPreviewOnline(true); setPreviewKey(value => value + 1); }
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
            `**SYSTEM ERROR DETECTED**\n\n${message}`,

          agent: "System Guard",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function restoreWorkingVersion() {
    if (loading || restoring) return;
    setRestoring(true);
    try {
      const response = await fetch(`${CLOUD_AGENT_URL}/restore`, { method: 'POST', headers: buildCloudAgentHeaders(true), body: JSON.stringify({ projectId }) });
      const result = await response.json();
      if (!response.ok || result.status !== 'success') throw new Error(result.message || 'Restore failed.');
      setPreviewUrl(result.url); setPreviewCode(''); setPreviewOnline(true); setPreviewKey(value => value + 1);
      setFailedPrompt(''); await refreshFiles();
      setMessages(previous => [...previous, { role: 'bot', text: result.message, agent: 'GeneSys' }]);
    } catch (error) { setMessages(previous => [...previous, { role: 'bot', text: error instanceof Error ? error.message : 'Restore failed.', agent: 'GeneSys' }]); }
    finally { setRestoring(false); }
  }

  async function handlePromote(index: number, checkpointId: string, promotionToken: string) {
    if (promotingCheckpoint) return;
    setPromotingCheckpoint(checkpointId);
    setMessages((previous) => previous.map((message, itemIndex) =>
      itemIndex === index
        ? { ...message, promotionError: undefined }
        : message
    ));

    try {
      const response = await fetch(`${CLOUD_AGENT_URL}/promote`, {
        method: "POST",
        headers: buildCloudAgentHeaders(true),
        body: JSON.stringify({ projectId, checkpointId, promotionToken }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== "success" || typeof data.url !== "string") {
        throw new Error(
          typeof data.message === "string"
            ? data.message
            : `Could not create the review pull request (${response.status}). Please try again.`
        );
      }
      setMessages((previous) => previous.map((message, itemIndex) =>
        itemIndex === index
          ? { ...message, promotionUrl: data.url }
          : message
      ));
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setMessages((previous) => previous.map((item, itemIndex) =>
        itemIndex === index
          ? { ...item, promotionError: message }
          : item
      ));
    } finally {
      setPromotingCheckpoint("");
    }
  }

  // ==========================================================
  // KEYBOARD
  // ==========================================================

  function handleInputKeyDown(
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      if (
        !loading &&
        input.trim()
      ) {
        void handleSend();
      }
    }
  }

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <AppShell
      projectTree={projectTree}
      previewUrl={previewUrl}
      previewOnline={previewOnline}
      onRefreshFiles={refreshFiles}
    >
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-background">
        {/* ==================================================
            HEADER
        ================================================== */}

        <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/95 px-3 backdrop-blur sm:px-5">
          <div className="flex min-w-0 items-center gap-3">
            <div className="hidden h-8 w-8 items-center justify-center rounded-xl bg-blue-50 text-blue-700 sm:flex">
              <Brain size={16} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[10px] font-medium text-slate-400">
                <span>Workspace</span>
                <span aria-hidden="true">/</span>
                <span className="font-semibold text-slate-600">App builder</span>
              </div>
              <div className="truncate text-xs font-semibold text-slate-900 sm:text-sm">
                {projectName}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button type="button" onClick={onProjects} disabled={loading || Boolean(promotingCheckpoint)} className="rounded-lg px-2 py-1 text-xs font-medium text-blue-700 disabled:opacity-50">Projects</button>
            <button type="button" onClick={() => setReportOpen(true)} className="rounded-lg px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50">Report a problem</button>
            <div className="mr-1 flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 xl:hidden" role="group" aria-label="Builder panels">
              <button
                type="button"
                onClick={() => setMobileView("chat")}
                aria-pressed={mobileView === "chat"}
                className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                    mobileView === "chat"
                    ? "bg-blue-600 text-white"
                    : "text-slate-500"
                }`}
              >
                Chat
              </button>
              <button
                type="button"
                onClick={() => setMobileView("preview")}
                aria-pressed={mobileView === "preview"}
                className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                    mobileView === "preview"
                    ? "bg-blue-600 text-white"
                    : "text-slate-500"
                }`}
              >
                Preview
              </button>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2.5 py-1.5 shadow-sm sm:px-3">
              <span
                className={`h-2 w-2 rounded-full ${
                  previewOnline
                    ? "bg-emerald-500 animate-pulse"
                    : "bg-slate-300"
                }`}
              />

              <span
                className={`hidden text-[10px] font-bold uppercase tracking-wider sm:inline ${
                  previewOnline
                    ? "text-emerald-600"
                    : "text-slate-400"
                }`}
              >
                {previewOnline
                  ? "Preview Ready"
                  : loading
                    ? "Building"
                    : "GeneSys Builder"}
              </span>
            </div>

            <button
              type="button"
              onClick={reloadPreview}
              disabled={loading || previewRefreshing || (!previewCode && !previewUrl)}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 disabled:opacity-30"
              title="Reconnect preview"
            >
              <RefreshCw size={17} />
            </button>

            <button
              type="button"
              onClick={openPreview}
              disabled={!previewCode && !previewUrl}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 disabled:opacity-30"
              title="Open preview"
            >
              <ExternalLink size={17} />
            </button>
          </div>
        </header>

        {/* ==================================================
            MAIN
        ================================================== */}

        <div className="flex min-h-0 flex-1 overflow-hidden">
          {/* =================================================
              CHAT
          ================================================= */}

          <aside className={`${mobileView === "chat" ? "flex" : "hidden"} min-h-0 w-full flex-col border-r border-slate-200/80 bg-white lg:w-[430px] xl:flex`}>
            <div
              ref={scrollRef}
              className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-gradient-to-b from-white to-slate-50/70 p-4 sm:p-5"
            >
              {messages.length === 0 && (
                <div className="rounded-3xl border border-slate-200 bg-white p-5 text-center shadow-sm shadow-slate-900/[0.03] sm:p-6">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 ring-1 ring-blue-100">
                    <Brain
                      size={24}
                      className="text-blue-500"
                    />
                  </div>

                  <h3 className="text-lg font-bold text-slate-900">
                    What would you like to build?
                  </h3>

                  <p className="mx-auto mt-2 max-w-xs text-xs leading-5 text-slate-500">
                    Start with a goal. You can refine the design after you see it working.
                  </p>

                  <div className="mt-5 space-y-2 text-left">
                    {[
                      "Build a simple appointment booking app",
                      "Create a dashboard for tracking expenses",
                      "Make a portfolio site for a photographer",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onClick={() => setInput(suggestion)}
                        className="group flex w-full items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3 text-left text-xs font-medium text-slate-600 shadow-sm shadow-slate-900/[0.02] transition hover:-translate-y-0.5 hover:border-blue-200 hover:bg-blue-50/50 hover:text-blue-800 hover:shadow-blue-900/[0.04]"
                      >
                        {suggestion}
                        <ArrowRight size={13} className="shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-blue-600" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map(
                (message, index) => (
                  <div
                    key={`${index}-${message.role}`}
                    className={`flex flex-col ${
                      message.role === "user"
                        ? "items-end"
                        : "items-start"
                    }`}
                  >
                    {message.agent && (
                      <div className="mb-1 ml-1 text-[9px] font-bold uppercase tracking-[0.2em] text-blue-600 opacity-50">
                        {message.agent}
                      </div>
                    )}

                    {message.thought && (
                      <div className="mb-3 w-full rounded-2xl border border-blue-100 bg-blue-50/50 p-3 text-[11px] italic text-blue-700">
                        <div className="mb-1 flex items-center gap-2 text-[8px] font-black uppercase tracking-widest not-italic opacity-50">
                          <Brain size={12} />
                          Reasoning
                        </div>

                        {message.thought}
                      </div>
                    )}

                    {message.plan && (
                      <div className="mb-3 w-full rounded-2xl border border-slate-200 bg-white p-3 text-[11px] text-slate-600">
                        <div className="mb-1 text-[8px] font-black uppercase tracking-widest text-slate-400">
                          Plan
                        </div>

                        {message.plan}
                      </div>
                    )}

                    <div
                      className={`max-w-[95%] rounded-2xl p-4 text-sm shadow-sm ${
                        message.role === "user"
                          ? "rounded-br-none bg-blue-600 text-white"
                          : "border border-slate-200 bg-white text-slate-700"
                      }`}
                    >
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.text}
                        </ReactMarkdown>
                      </div>
                    </div>

                    {message.hasFile && (
                      <div className="mt-3 w-full rounded-xl border border-emerald-100 bg-emerald-50 p-3">
                        <div className="mb-2 flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest text-emerald-600">
                          <Check size={12} />
                          Files synchronized
                        </div>

                        <div className="space-y-1">
                          {message.modifiedFiles?.map(
                            (file) => (
                              <div
                                key={file}
                                className="flex items-center gap-2 rounded-lg border border-emerald-100 bg-white px-2 py-1.5 font-mono text-[10px] text-emerald-700"
                              >
                                <FileCode
                                  size={12}
                                />

                                {file}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {message.buildAttempted &&
                      message.buildPassed ===
                        false && (
                        <div className="mt-3 flex w-full items-center gap-2 rounded-xl border border-red-100 bg-red-50 p-3 text-[10px] font-bold text-red-600">
                          <AlertCircle
                            size={14}
                          />
                          Build reported errors.
                        </div>
                      )}

                    {message.role === "bot" &&
                      message.buildPassed === true &&
                      message.browserVerified === true &&
                      message.checkpointStatus === "success" &&
                      message.checkpointId &&
                      message.promotionToken && (
                      <div className="mt-3 w-full rounded-xl border border-blue-100 bg-blue-50 p-3">
                        <div className="mb-2 text-[10px] font-semibold text-blue-900">
                          Build passed and browser verification completed.
                        </div>
                        {message.promotionUrl ? (
                          <a
                            href={message.promotionUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                          >
                            Review production pull request <ExternalLink size={13} />
                          </a>
                        ) : (
                          <button
                            type="button"
                            disabled={Boolean(promotingCheckpoint)}
                            onClick={() => void handlePromote(index, message.checkpointId!, message.promotionToken!)}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                          >
                            {promotingCheckpoint === message.checkpointId ? (
                              <Loader2 size={13} className="animate-spin" />
                            ) : (
                              <ExternalLink size={13} />
                            )}
                            {promotingCheckpoint === message.checkpointId
                              ? "Creating pull request..."
                              : "Create review pull request"}
                          </button>
                        )}
                        {message.promotionError && (
                          <p role="alert" className="mt-2 text-xs text-red-700">{message.promotionError}</p>
                        )}
                        <p className="mt-2 text-[10px] text-blue-700">This opens a pull request for review; it does not deploy or merge automatically.</p>
                      </div>
                    )}
                  </div>
                )
              )}

              {loading && (
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-400">
                  <Loader2
                    size={16}
                    className="animate-spin text-blue-500"
                  />

                    {progressStage} ? {elapsed}s
                </div>
              )}
            </div>

            {/* =================================================
                INPUT
            ================================================= */}

            <div className="border-t border-slate-200/80 bg-white p-3 sm:p-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-2 transition-all focus-within:border-blue-300 focus-within:bg-white focus-within:shadow-[0_12px_36px_-20px_rgba(37,99,235,0.35)]">
                {failedPrompt && <div role="status" className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  <p>{previewUrl ? 'Your previous working preview is still available.' : 'The request did not finish. You can retry it.'}</p>
                  <div className="mt-2 flex flex-wrap gap-3">
                    <button type="button" disabled={loading || restoring} onClick={() => void handleSend(failedPrompt)} className="font-semibold underline">Retry request</button>
                    {previewUrl && <button type="button" disabled={loading || restoring} onClick={() => void restoreWorkingVersion()} className="font-semibold underline">{restoring ? 'Restoring…' : 'Restore last working version'}</button>}
                  </div>
                  {previewUrl && <p className="mt-2 text-xs">Restoring replaces the app files; current edits are backed up.</p>}
                </div>}
                <textarea
                  value={input}
                  onChange={(event) =>
                    setInput(
                      event.target.value
                    )
                  }
                  onKeyDown={
                    handleInputKeyDown
                  }
                  placeholder="Describe what you want to build or change..."
                  aria-label="Describe what you want to build or change"
                  rows={3}
                  disabled={loading}
                  className="w-full resize-none bg-transparent px-4 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400"
                />

                <div className="flex items-center justify-between px-2 pb-1">
                  <span className="text-[10px] text-slate-400">Enter to send · Shift + Enter for a new line</span>
                    <button
                      type="button"
                      onClick={() =>
                        void handleSend()
                      }
                      aria-label={loading ? "Working on your request" : "Send request"}
                    disabled={
                      loading ||
                      !input.trim()
                    }
                    className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20 transition hover:-translate-y-0.5 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {loading ? (
                      <Loader2
                        className="animate-spin"
                        size={18}
                      />
                    ) : (
                      <Send size={18} />
                    )}
                  </button>
                </div>
              </div>

              <div className="mt-2 text-center text-[10px] text-slate-400">
                GeneSys Builder · describe, preview, refine
              </div>
            </div>
          </aside>

          {/* =================================================
              PREVIEW
          ================================================= */}

          <section className={`${mobileView === "preview" ? "flex" : "hidden"} min-w-0 flex-1 flex-col bg-[#f1f5f9] xl:flex`}>
            <div className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-5">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${previewOnline ? "bg-emerald-500" : loading ? "animate-pulse bg-amber-400" : "bg-slate-300"}`} />

                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  {previewOnline ? "Live preview" : loading ? progressStage : "Preview"}
                </span>
              </div>

              {(previewCode || previewUrl) && (
                <button
                  type="button"
                  onClick={reloadPreview}
                  className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 transition hover:bg-slate-100"
                >
                  <RefreshCw size={13} />
                  Reload
                </button>
              )}
            </div>

            {previewUrl && (
              <div className="border-b border-slate-200 bg-white px-4 py-2 text-xs text-slate-600">
                <span role="status">{previewError || (previewRefreshing ? "Reconnecting preview..." : "Preview not visible? Reconnect the link or open it in a new tab. Network filters may block preview domains.")}</span>
                <button type="button" disabled={previewRefreshing || loading} onClick={() => void reloadPreview()} className="ml-2 font-semibold text-blue-700 disabled:opacity-50">Reconnect</button>
                <button type="button" onClick={openPreview} className="ml-2 font-semibold text-blue-700">Open preview</button>
              </div>
            )}
            <div className="min-h-0 flex-1 p-3 sm:p-6">
              <div className="relative h-full w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_70px_-40px_rgba(15,23,42,0.35)] sm:rounded-[1.5rem]">
                {previewUrl || previewCode ? (
                  <iframe
                    key={previewKey}
                    src={previewUrl || undefined}
                    srcDoc={previewUrl ? undefined : previewCode}
                    title="GeneSys Simulation Preview"
                    className="h-full w-full border-none"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                    onLoad={() => setPreviewOnline(true)}
                    onError={() => { setPreviewOnline(false); setPreviewError("Preview could not load. Reconnect it or try another network if a security filter blocks the link."); }}
                  />
                ) : (
                  <div className="flex h-full flex-col items-center justify-center text-center">
                    <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-blue-50 ring-1 ring-blue-100">
                      <FileCode
                        size={28}
                        className="text-blue-500"
                      />
                    </div>

                    <div className="text-sm font-semibold tracking-tight text-slate-800">
                      Your preview will appear here
                    </div>

                    <p className="mt-2 max-w-sm px-5 text-xs leading-5 text-slate-500">
                      Describe an app idea in the conversation. Once GeneSys finishes the first build, you can explore it here and ask for changes.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
      {reportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/30 p-4">
          <section role="dialog" aria-modal="true" aria-labelledby="report-title" onKeyDown={event => { if (event.key === "Escape") setReportOpen(false); }} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 id="report-title" className="text-lg font-semibold">Report a beta problem</h2>
            <p className="mt-2 text-xs text-slate-500">Your project and request reference will be included. Please leave passwords and API keys out of your report.</p>
            <textarea aria-label="Describe the problem" maxLength={2000} value={reportText} onChange={event => setReportText(event.target.value)} className="mt-4 h-28 w-full rounded-lg border border-slate-200 p-3 text-sm" />
            <p role="status" className="mt-2 break-all text-xs text-slate-600">{reportStatus}</p>
            <div className="mt-4 flex gap-3">
              <button type="button" disabled={reportSending || !reportText.trim()} onClick={() => void sendReport()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">{reportSending ? "Sending..." : "Send report"}</button>
              <button type="button" onClick={() => setReportOpen(false)} className="px-4 py-2 text-sm text-slate-600">Close</button>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}

// ============================================================
// ROUTE
// ============================================================

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/build",
  validateSearch: (search: Record<string, unknown>) => ({ projectId: typeof search.projectId === 'string' ? search.projectId : '' }),
  component: OwnedBuilder,
});

function OwnedBuilder() {
  const { projectId } = Route.useSearch()
  const [state, setState] = useState<'loading' | 'ready' | 'signin' | 'error'>('loading')
  const [name, setName] = useState('')
  const [message, setMessage] = useState('')
  useEffect(() => {
    let active = true
    setState('loading')
    if (!supabase) { setState('error'); setMessage('Authentication is not configured.'); return }
    async function load() {
      const { data: { session }, error } = await supabase!.auth.getSession()
      if (!active) return
      if (error) throw error
      if (!session) { setState('signin'); return }
      const { data, error: lookupError } = await supabase!.from('projects').select('id,name').eq('id', projectId).single()
      if (lookupError || !data) throw new Error('Project not found or access denied.')
      if (active) { setName(data.name); setState('ready') }
    }
    if (projectId) void load().catch(error => { if (active) { setMessage(error.message || 'Unable to open project.'); setState('error') } })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => { if (active && event === 'SIGNED_OUT') setState('signin') })
    return () => { active = false; subscription.unsubscribe() }
  }, [projectId])
  if (!projectId) return <Navigate to="/account" />
  if (state === 'signin') return <Navigate to="/auth" />
  if (state === 'ready') return <BuildPage key={projectId} projectId={projectId} projectName={name} onProjects={() => { window.location.href = '/account' }} />
  return <main className="min-h-screen bg-slate-50 p-12 text-slate-900"><p role="status">{state === 'loading' ? 'Opening your project…' : message}</p><a className="mt-5 block text-blue-600" href="/account">Return to dashboard</a></main>
}

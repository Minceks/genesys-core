import React from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowUpRight,
  Cpu,
  Eye,
  FileCode2,
  FolderKanban,
  LayoutDashboard,
  RefreshCw,
} from "lucide-react";

type AppShellProps = {
  children: React.ReactNode;
  projectTree: {
    routes: string[];
    components: string[];
  };
  previewUrl: string;
  previewOnline: boolean;
  onRefreshFiles: () => void;
};

export function AppShell({
  children,
  projectTree,
  previewUrl,
  previewOnline,
  onRefreshFiles,
}: AppShellProps) {
  return (
    <div className="h-[100dvh] overflow-hidden bg-slate-50 text-slate-900">
      <div className="flex h-full min-h-0 overflow-hidden">
        <aside className="hidden w-[250px] shrink-0 flex-col border-r border-slate-200 bg-white px-4 py-5 lg:flex">
          <div className="flex items-center justify-between px-1">
            <Link to="/" className="flex items-center gap-2.5 no-underline">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm shadow-blue-600/20"><Cpu size={19} /></span>
              <span className="text-sm font-extrabold tracking-[-0.04em] text-slate-950">GeneSys<span className="text-blue-600">.</span></span>
            </Link>
            <Link to="/account" aria-label="Back to dashboard" className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 no-underline transition hover:bg-slate-100 hover:text-slate-700"><ArrowUpRight size={16} /></Link>
          </div>

          <div className="mt-8 space-y-1">
            <Link to="/account" className="flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-xs font-medium text-slate-600 no-underline transition hover:bg-slate-50 hover:text-blue-700"><LayoutDashboard size={16} /> Workspace</Link>
            <div className="flex items-center gap-2.5 rounded-xl bg-blue-50 px-3 py-2.5 text-xs font-semibold text-blue-700"><FolderKanban size={16} /> App builder</div>
          </div>

          <div className="mt-8 min-h-0 flex-1 overflow-y-auto">
            <div className="mb-3 flex items-center justify-between px-2">
              <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">
                <FileCode2 size={13} /> Project files
              </div>
              <button type="button" onClick={onRefreshFiles} className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 transition hover:bg-blue-50 hover:text-blue-700" title="Refresh project files" aria-label="Refresh project files">
                <RefreshCw size={13} />
              </button>
            </div>

            <FileGroup title="Routes" files={projectTree.routes} empty="No routes yet" />
            <FileGroup title="Components" files={projectTree.components} empty="No components yet" />
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-3.5 shadow-sm shadow-slate-900/[0.02]">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
              <span className={`h-2 w-2 rounded-full ${previewOnline ? "bg-emerald-500" : previewUrl ? "animate-pulse bg-amber-400" : "bg-slate-300"}`} />
              {previewOnline ? "Preview is ready" : previewUrl ? "Connecting to preview" : "Waiting for a preview"}
            </div>
            <div className="mt-2 flex items-center gap-2 text-[10px] leading-4 text-slate-500">
              <Eye size={13} className="shrink-0 text-blue-600" />
              Your live app will appear beside the conversation.
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

function FileGroup({ title, files, empty }: { title: string; files: string[]; empty: string }) {
  return (
    <section className="mb-6">
      <div className="mb-2 px-2 text-[10px] font-semibold text-slate-400">{title}</div>
      {files.length === 0 ? (
        <div className="rounded-lg px-2 py-2 text-xs text-slate-400">{empty}</div>
      ) : (
        <ul className="space-y-0.5">
          {files.map((file) => (
            <li key={file} title={file} className="truncate rounded-lg px-2 py-2 text-[11px] text-slate-600 transition hover:bg-slate-50 hover:text-blue-700">{file}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

import { Link } from "@tanstack/react-router";
import { Cpu } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <Link to="/" className="inline-flex items-center gap-2 text-sm font-bold tracking-tight text-slate-900 no-underline">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-white"><Cpu size={15} /></span>
          GeneSys
        </Link>
        <p className="text-xs text-slate-500">Build, preview, and review with GeneSys.</p>
        <div className="flex items-center gap-5 text-xs font-medium text-slate-500">
          <Link to="/pricing" className="no-underline transition hover:text-blue-700">Pricing</Link>
          <Link to="/terms" className="no-underline transition hover:text-blue-700">Terms</Link>
          <Link to="/dashboard" className="no-underline transition hover:text-blue-700">Dashboard</Link>
        </div>
      </div>
    </footer>
  );
}

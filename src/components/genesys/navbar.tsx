import { Link } from "@tanstack/react-router";
import React from "react";
import { supabase } from "@/lib/supabase";
import { ArrowUpRight, Cpu, Menu, X } from "lucide-react";

export function Navbar() {
  const [isOpen, setIsOpen] = React.useState(false);
  const [signedIn, setSignedIn] = React.useState(false);

  React.useEffect(() => {
    if (!supabase) return;
    let active = true;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setSignedIn(Boolean(session));
    });
    supabase.auth.getSession().then(({ data }) => {
      if (active) setSignedIn(Boolean(data.session));
    }).catch(() => { /* Keep the sign-in link available. */ });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  const closeMenu = () => setIsOpen(false);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
      <nav
        className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8"
        aria-label="Main navigation"
      >
        <Link
          to="/"
          className="group flex items-center gap-2.5 no-underline"
          onClick={closeMenu}
          aria-label="GeneSys home"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20 transition-transform group-hover:-rotate-3">
            <Cpu size={21} strokeWidth={2.3} />
          </span>
          <span className="text-[17px] font-extrabold tracking-[-0.04em] text-slate-950">
            GeneSys<span className="text-blue-600">.</span>
          </span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          <a href="/#features" className="text-sm font-medium text-slate-600 transition hover:text-blue-700">Features</a>
          <a href="/#how-it-works" className="text-sm font-medium text-slate-600 transition hover:text-blue-700">How it works</a>
          <Link to="/pricing" className="text-sm font-medium text-slate-600 no-underline transition hover:text-blue-700">Pricing</Link>
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <Link to={signedIn ? "/account" : "/auth"} className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-700 no-underline transition hover:bg-slate-100">
            {signedIn ? "My dashboard" : "Sign in"}
          </Link>
          <Link to="/build" className="glow-button inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold no-underline transition hover:-translate-y-0.5">
            Open builder <ArrowUpRight size={16} />
          </Link>
        </div>

        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-700 transition hover:bg-slate-50 md:hidden"
          onClick={() => setIsOpen((open) => !open)}
          aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={isOpen}
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {isOpen && (
        <div className="border-t border-slate-100 bg-white px-5 py-4 shadow-lg md:hidden">
          <div className="mx-auto flex max-w-7xl flex-col gap-1">
            <a href="/#features" onClick={closeMenu} className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">Features</a>
            <a href="/#how-it-works" onClick={closeMenu} className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">How it works</a>
            <Link to="/pricing" onClick={closeMenu} className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 no-underline hover:bg-slate-50">Pricing</Link>
            <Link to={signedIn ? "/account" : "/auth"} onClick={closeMenu} className="rounded-lg px-3 py-3 text-sm font-medium text-slate-700 no-underline hover:bg-slate-50">{signedIn ? "My dashboard" : "Sign in"}</Link>
            <Link to="/build" onClick={closeMenu} className="glow-button mt-2 inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold no-underline">
              Start building <ArrowUpRight size={16} />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

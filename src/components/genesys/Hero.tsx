import { Link } from "@tanstack/react-router";
import { ArrowRight, Check, Code2, Sparkles, Layers, MousePointer2 } from "lucide-react";
import "./polish.css";

export function Hero() {
  return <section className="genesys-hero relative overflow-hidden bg-white">
    <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 pb-16 pt-14 sm:px-8 sm:py-24 lg:grid-cols-[1fr_1fr]">
      <div className="relative z-10">
        <span className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700"><span className="h-1.5 w-1.5 rounded-full bg-blue-600" /> Made for your next idea <span className="border-l border-blue-200 pl-2 text-blue-500">BETA</span></span>
        <h1 className="mt-7 text-5xl font-semibold leading-[1.06] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-7xl">Big ideas.<br />Small first step.<br /><span className="text-blue-600">Just describe it.</span></h1>
        <p className="mt-6 max-w-lg text-base leading-7 text-slate-500 sm:text-lg">Turn the app in your head into something you can try. Build with a conversation, explore the preview, and make it yours.</p>
        <div className="mt-8 flex flex-wrap gap-3"><Link to="/build" className="inline-flex items-center gap-3 rounded-2xl bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700">Create your first project <ArrowRight size={17} /></Link><a href="#how-it-works" className="inline-flex items-center rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-semibold text-slate-600 hover:bg-slate-50">Explore how it works</a></div>
        <div className="mt-6 flex flex-wrap gap-4 text-xs text-slate-500">{['Your own workspace', 'Live previews', 'Build at your pace'].map(text => <span key={text} className="inline-flex items-center gap-1.5"><Check size={13} className="text-blue-600" />{text}</span>)}</div>
      </div>
      <div className="relative min-w-0 rounded-[2rem] border border-blue-100 bg-blue-50/60 p-4 sm:p-7">
        <div className="mb-4 flex items-center justify-between px-1 text-xs font-medium text-blue-500"><span className="inline-flex items-center gap-2"><Layers size={14} /> From prompt to project</span><span>Illustrative preview</span></div>
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_24px_60px_-25px_rgba(37,99,235,0.25)]">
          <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3"><span className="h-2 w-2 rounded-full bg-slate-300" /><span className="h-2 w-2 rounded-full bg-slate-200" /><span className="h-2 w-2 rounded-full bg-slate-200" /><span className="ml-3 text-xs text-slate-400">Studio / My portfolio</span></div>
          <div className="p-5 sm:p-7"><div className="flex items-center justify-between"><span className="text-sm font-semibold tracking-tight text-slate-900">FORM & FIELD</span><span className="text-[10px] text-slate-400">WORK / ABOUT / CONTACT</span></div><h2 className="mb-5 mt-9 text-3xl font-medium leading-tight tracking-tight text-slate-900 sm:text-4xl">Spaces worth<br /><span className="text-slate-400">slowing down for.</span></h2><div className="grid grid-cols-2 gap-3"><div className="hero-space hero-space-one h-36 rounded-xl sm:h-44" /><div className="hero-space hero-space-two h-36 rounded-xl sm:h-44" /></div><div className="mt-3 flex justify-between text-[10px] text-slate-400"><span>Selected interiors, 2026</span><span>01 / 02</span></div></div>
        </div>
        <div className="relative mx-2 -mt-1 rounded-2xl border border-blue-100 bg-white p-4 shadow-lg shadow-blue-900/5 sm:mx-5"><div className="flex gap-3"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><Sparkles size={17} /></span><div><p className="text-xs font-semibold text-slate-800">?Build a minimal portfolio for my design studio.?</p><p className="mt-1.5 text-xs text-slate-400">Your idea is the starting point.</p></div></div></div>
        <div className="mt-5 flex justify-center gap-5 text-[11px] font-medium text-blue-500"><span className="inline-flex items-center gap-1.5"><Code2 size={13} /> Build</span><span className="inline-flex items-center gap-1.5"><MousePointer2 size={13} /> Try</span><span className="inline-flex items-center gap-1.5"><Sparkles size={13} /> Refine</span></div>
      </div>
    </div>
  </section>;
}

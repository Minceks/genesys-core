import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Check,
  CirclePlay,
  Code2,
  Globe2,
  Sparkles,
} from "lucide-react";

export function Hero() {
  return (
    <section className="relative isolate overflow-hidden bg-white">
      <div className="pointer-events-none absolute -right-40 -top-48 -z-10 h-[520px] w-[520px] rounded-full bg-blue-100/70 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-64 left-[22%] -z-10 h-[440px] w-[440px] rounded-full bg-sky-50 blur-3xl" />

      <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 pb-20 pt-16 sm:px-8 sm:pb-24 sm:pt-20 lg:grid-cols-[0.88fr_1.12fr] lg:gap-12 lg:pb-28 lg:pt-24">
        <div className="max-w-2xl">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50/80 px-3.5 py-2 text-xs font-semibold text-blue-700">
            <Sparkles size={14} />
            Your idea, built with AI
          </div>

          <h1 className="text-5xl font-semibold leading-[1.04] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-[4.35rem]">
            From your idea to a real,
            <span className="text-gradient-brand"> working app.</span>
          </h1>

          <p className="mt-6 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
            Describe what you want to make. GeneSys plans the work, builds your
            project, and gives you a live preview you can shape with each new
            prompt.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link to="/build" className="glow-button inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-semibold no-underline transition hover:-translate-y-0.5">
              Start building <ArrowRight size={17} />
            </Link>
            <a href="#how-it-works" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-semibold text-slate-700 no-underline shadow-sm transition hover:border-blue-200 hover:bg-blue-50/50">
              <CirclePlay size={17} className="text-blue-600" />
              See how it works
            </a>
          </div>

          <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-slate-500">
            <span className="inline-flex items-center gap-1.5"><Check size={14} className="text-blue-600" /> Start from a prompt</span>
            <span className="inline-flex items-center gap-1.5"><Check size={14} className="text-blue-600" /> See changes live</span>
            <span className="inline-flex items-center gap-1.5"><Check size={14} className="text-blue-600" /> Keep iterating</span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[660px] lg:ml-auto">
          <div className="absolute -inset-4 -z-10 rounded-[2.5rem] bg-gradient-to-br from-blue-100 via-white to-sky-100 blur-xl" />
          <div className="overflow-hidden rounded-[1.6rem] border border-slate-200 bg-white shadow-[0_28px_90px_-38px_rgba(30,64,175,0.3)]">
            <div className="flex h-12 items-center gap-3 border-b border-slate-100 px-4">
              <div className="flex gap-1.5" aria-hidden="true">
                <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
              </div>
              <div className="flex h-7 min-w-0 flex-1 items-center gap-2 rounded-md bg-slate-50 px-2.5 text-[10px] text-slate-400">
                <Globe2 size={12} />
                <span className="truncate">preview.genesys.app / orbit-analytics</span>
              </div>
              <div className="hidden items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-[9px] font-semibold text-emerald-700 sm:flex">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Live
              </div>
            </div>

            <div className="grid min-h-[330px] sm:grid-cols-[190px_1fr]">
              <div className="hidden flex-col border-r border-slate-100 bg-slate-50/70 p-4 sm:flex">
                <div className="mb-5 flex items-center gap-2 text-xs font-bold text-slate-800">
                  <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-blue-600 text-[10px] text-white">O</span>
                  Orbit workspace
                </div>
                <div className="rounded-xl border border-blue-100 bg-white p-3 shadow-sm">
                  <div className="mb-2 flex items-center gap-1.5 text-[9px] font-semibold text-blue-700"><Sparkles size={11} /> GeneSys</div>
                  <p className="text-[10px] leading-4 text-slate-600">Create a clean analytics dashboard for my team.</p>
                </div>
                <div className="mt-auto pt-5">
                  <div className="mb-2 flex items-center gap-1.5 text-[9px] font-semibold text-slate-400"><Code2 size={11} /> PROJECT FILES</div>
                  <div className="space-y-1 text-[10px] text-slate-500">
                    <div className="rounded-md bg-blue-50 px-2 py-1.5 text-blue-700">⌄ src</div>
                    <div className="pl-5">⌄ routes</div>
                    <div className="rounded-md bg-white px-2 py-1.5 pl-8 text-slate-700 shadow-sm">dashboard.tsx</div>
                    <div className="pl-5">⌄ components</div>
                    <div className="pl-8">stat-card.tsx</div>
                  </div>
                </div>
              </div>

              <div className="min-w-0 bg-white p-4 sm:p-5">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-semibold uppercase tracking-[0.15em] text-blue-600">Workspace overview</div>
                    <div className="mt-1 text-sm font-bold text-slate-900 sm:text-base">Good morning, Alex</div>
                  </div>
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-blue-700">AL</span>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  {[
                    { label: "Active users", value: "2,840", change: "+12.8%" },
                    { label: "Conversion", value: "8.42%", change: "+2.4%" },
                    { label: "New signups", value: "468", change: "+9.1%" },
                    { label: "Revenue", value: "$24.6k", change: "+6.3%" },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-xl border border-slate-100 p-3 sm:p-3.5">
                      <div className="text-[9px] font-medium text-slate-400">{stat.label}</div>
                      <div className="mt-1 text-lg font-bold tracking-tight text-slate-900 sm:text-xl">{stat.value}</div>
                      <div className="mt-1 text-[9px] font-semibold text-emerald-600">{stat.change} this month</div>
                    </div>
                  ))}
                </div>

                <div className="mt-3 rounded-xl border border-slate-100 p-3.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="font-semibold text-slate-700">Activity over time</span>
                    <span className="text-slate-400">Last 7 days</span>
                  </div>
                  <div className="mt-4 flex h-[76px] items-end gap-1.5" aria-hidden="true">
                    {[32, 46, 39, 64, 52, 76, 60, 88, 68, 96, 73, 100, 82, 92, 68, 84, 57, 76, 62, 89, 71, 98, 79, 93].map((height, index) => (
                      <span key={index} style={{ height: `${height}%` }} className={`flex-1 rounded-t-sm ${index > 19 ? "bg-blue-600" : "bg-blue-200"}`} />
                    ))}
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-[9px] font-medium text-blue-800">
                  <Check size={12} /> Your project preview updates as GeneSys builds
                </div>
              </div>
            </div>
          </div>

          <div className="absolute -bottom-5 -left-3 hidden items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-3 shadow-lg sm:flex lg:-left-8">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"><Check size={16} /></span>
            <span><span className="block text-[10px] font-bold text-slate-800">Build complete</span><span className="block text-[9px] text-slate-500">Preview is ready to explore</span></span>
          </div>
        </div>
      </div>
    </section>
  );
}

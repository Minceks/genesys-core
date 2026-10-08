import { createRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleHelp,
  Code2,
  Cpu,
  FolderOpen,
  LayoutDashboard,
  Plus,
  Settings2,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import { apiRequest } from "@/utils/api";
import { Route as rootRoute } from "./__root";

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/dashboard",
  component: DashboardPage,
});

type HealthResponse = {
  status: string;
  agent: boolean;
  daytona: boolean;
  groq: boolean;
};

function DashboardPage() {
  const { data: health, isLoading, isError } = useQuery({
    queryKey: ["api-health"],
    queryFn: () => apiRequest<HealthResponse>("/health"),
    refetchInterval: 30000,
    retry: 1,
  });

  const connectionState = isLoading
    ? "Checking connection"
    : isError || !health?.agent
      ? "Connection issue"
      : "All systems ready";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 lg:flex">
      <aside className="flex border-b border-slate-200 bg-white px-5 py-4 lg:min-h-screen lg:w-[248px] lg:shrink-0 lg:flex-col lg:border-b-0 lg:border-r lg:px-4 lg:py-6">
        <Link to="/" className="flex shrink-0 items-center gap-2.5 px-1 no-underline">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20"><Cpu size={19} /></span>
          <span className="text-base font-extrabold tracking-[-0.04em] text-slate-950">GeneSys<span className="text-blue-600">.</span></span>
        </Link>

        <div className="ml-auto flex items-center gap-2 lg:ml-0 lg:mt-10 lg:flex-col lg:items-stretch">
          <div className="hidden px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400 lg:block">Workspace</div>
          <Link to="/dashboard" className="flex items-center gap-3 rounded-xl bg-blue-50 px-3 py-2.5 text-sm font-semibold text-blue-700 no-underline">
            <LayoutDashboard size={17} /> Overview
          </Link>
          <Link to="/build" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 no-underline transition hover:bg-slate-50 hover:text-slate-950">
            <WandSparkles size={17} /> Builder <ArrowUpRight size={14} className="ml-auto hidden text-slate-400 lg:block" />
          </Link>
        </div>

        <div className="mt-auto hidden rounded-2xl border border-slate-200 bg-slate-50 p-4 lg:block">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
            <span className={`h-2 w-2 rounded-full ${health?.agent ? "bg-emerald-500" : "bg-amber-400"}`} />
            {connectionState}
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">GeneSys checks your cloud agent automatically.</p>
          <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-400">
            <span className={health?.daytona ? "text-emerald-600" : "text-slate-400"}>Workspace</span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className={health?.groq ? "text-emerald-600" : "text-slate-400"}>AI agent</span>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <header className="flex h-[72px] items-center justify-between border-b border-slate-200 bg-white px-5 sm:px-8">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span className="hidden sm:inline">Workspace</span>
            <ChevronRight size={15} className="hidden text-slate-300 sm:block" />
            <span className="font-semibold text-slate-900">Overview</span>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/pricing" className="hidden rounded-xl px-3 py-2 text-sm font-medium text-slate-600 no-underline transition hover:bg-slate-50 sm:inline-flex">Plans</Link>
            <Link to="/build" className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-3.5 py-2.5 text-sm font-semibold text-white no-underline shadow-sm shadow-blue-600/20 transition hover:bg-blue-700">
              <Plus size={16} /> New project
            </Link>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <div className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-blue-600">Your workspace</div>
              <h1 className="text-3xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-4xl">What will you make today?</h1>
              <p className="mt-2 text-sm leading-6 text-slate-600">Create a new app or keep moving on a project you already started.</p>
            </div>
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm">
              <span className={`h-2 w-2 rounded-full ${health?.agent ? "bg-emerald-500" : isError ? "bg-rose-500" : "animate-pulse bg-amber-400"}`} />
              {connectionState}
            </div>
          </div>

          <section className="mt-8 grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(270px,0.75fr)]">
            <div className="relative overflow-hidden rounded-[1.75rem] bg-gradient-to-br from-blue-700 via-blue-600 to-indigo-600 p-7 text-white shadow-xl shadow-blue-900/10 sm:p-9">
              <div className="pointer-events-none absolute -right-10 -top-16 h-64 w-64 rounded-full border-[35px] border-white/5" />
              <div className="pointer-events-none absolute -bottom-32 right-24 h-64 w-64 rounded-full bg-sky-300/20 blur-3xl" />
              <div className="relative max-w-xl">
                <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-blue-50 ring-1 ring-white/15"><Sparkles size={13} /> GeneSys Builder</span>
                <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-[-0.04em] sm:text-4xl">Bring your next idea to life.</h2>
                <p className="mt-3 max-w-md text-sm leading-6 text-blue-100">Describe the app you have in mind. GeneSys will plan it, build the project, and open a live preview for you to explore.</p>
                <Link to="/build" className="mt-7 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-semibold text-blue-700 no-underline shadow-lg transition hover:-translate-y-0.5 hover:bg-blue-50">
                  Open the builder <ArrowRight size={16} />
                </Link>
                <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] font-medium text-blue-100">
                  <span className="inline-flex items-center gap-1.5"><Check size={13} /> Start with a prompt</span>
                  <span className="inline-flex items-center gap-1.5"><Check size={13} /> Iterate with live preview</span>
                </div>
              </div>
              <div className="absolute bottom-7 right-8 hidden h-24 w-32 rotate-3 items-center justify-center rounded-2xl border border-white/20 bg-white/10 backdrop-blur sm:flex">
                <div className="grid grid-cols-3 gap-1.5">
                  {Array.from({ length: 9 }, (_, i) => <span key={i} className={`h-5 w-5 rounded-md ${i === 4 ? "bg-white" : "bg-white/20"}`} />)}
                </div>
              </div>
            </div>

            <aside className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-400"><Activity size={15} className="text-blue-600" /> Your workflow</div>
              <ol className="mt-6 space-y-5">
                {[
                  { n: "01", title: "Describe your idea", text: "Say what your app should do and who it is for.", icon: Sparkles },
                  { n: "02", title: "Review the build", text: "Follow the plan, files, and build progress as it runs.", icon: Code2 },
                  { n: "03", title: "Explore the preview", text: "Try the result and request the next change.", icon: FolderOpen },
                ].map(({ n, title, text, icon: Icon }, index) => (
                  <li key={n} className="relative flex gap-3.5">
                    {index < 2 && <span className="absolute left-[17px] top-10 h-8 w-px bg-slate-200" />}
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100"><Icon size={16} /></span>
                    <div className="min-w-0 pb-1">
                      <div className="text-[10px] font-bold text-blue-600">STEP {n}</div>
                      <h3 className="mt-0.5 text-sm font-semibold text-slate-900">{title}</h3>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{text}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <Link to="/pricing" className="mt-5 flex items-center gap-2 border-t border-slate-100 pt-4 text-xs font-semibold text-slate-600 no-underline transition hover:text-blue-700">
                <Settings2 size={14} /> Compare plans <ArrowRight size={13} className="ml-auto" />
              </Link>
            </aside>
          </section>

          <section className="mt-10">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-slate-950">Projects</h2>
                <p className="mt-1 text-xs text-slate-500">Your work, ready when you are.</p>
              </div>
              <Link to="/build" className="hidden items-center gap-1 text-xs font-semibold text-blue-700 no-underline hover:text-blue-800 sm:inline-flex">Open builder <ArrowRight size={14} /></Link>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <Link to="/build" className="group flex min-h-[190px] flex-col rounded-2xl border border-dashed border-blue-300 bg-blue-50/40 p-5 no-underline transition hover:border-blue-500 hover:bg-blue-50 hover:shadow-md hover:shadow-blue-900/5">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm shadow-blue-600/20"><Plus size={19} /></span>
                <span className="mt-5 text-sm font-semibold text-slate-900">Start a new project</span>
                <span className="mt-1 text-xs leading-5 text-slate-500">Describe an idea and let GeneSys create the first version.</span>
                <span className="mt-auto flex items-center gap-1 pt-4 text-xs font-semibold text-blue-700">Create project <ArrowRight size={13} className="transition-transform group-hover:translate-x-1" /></span>
              </Link>

              <div className="flex min-h-[190px] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-6 text-center md:col-span-1 xl:col-span-2">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-50 text-slate-400"><FolderOpen size={20} /></span>
                <h3 className="mt-3 text-sm font-semibold text-slate-900">Your projects will show up here</h3>
                <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">Start a build to create your first project. You can come back here to pick up where you left off.</p>
                <Link to="/build" className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 no-underline hover:text-blue-800">Create your first project <ArrowRight size={13} /></Link>
              </div>
            </div>
          </section>

          <div className="mt-8 flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><CircleHelp size={17} /></span>
              <div><div className="text-xs font-semibold text-slate-900">Need a hand getting started?</div><div className="mt-0.5 text-[11px] text-slate-500">Tell GeneSys what you want to build in your own words.</div></div>
            </div>
            <Link to="/build" aria-label="Go to builder" className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 no-underline transition hover:bg-blue-50 hover:text-blue-700"><ArrowUpRight size={17} /></Link>
          </div>
        </div>
      </main>
    </div>
  );
}

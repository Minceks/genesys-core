import {
  Braces,
  Eye,
  GitBranch,
  Layers3,
  WandSparkles,
} from "lucide-react";

const featureList = [
  {
    title: "Start with a clear plan",
    desc: "Turn a rough idea into a practical build plan before the agent changes your project.",
    icon: WandSparkles,
  },
  {
    title: "Build real project files",
    desc: "GeneSys works in a project workspace, so your app is more than a static mockup.",
    icon: Braces,
  },
  {
    title: "See every change",
    desc: "Keep your project files and live preview close while you refine the result in chat.",
    icon: Eye,
  },
  {
    title: "Iterate at your pace",
    desc: "Ask for the next change in plain language and keep moving toward the experience you want.",
    icon: GitBranch,
  },
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-20 bg-slate-50 py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-blue-600">A better way to get started</div>
          <h2 className="text-3xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-4xl">
            Go from prompt to <span className="text-blue-600">something you can use.</span>
          </h2>
          <p className="mt-4 text-base leading-7 text-slate-600">
            Keep the important parts of building in one calm workspace: the plan,
            the project, and the preview.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {featureList.map(({ title, desc, icon: Icon }, index) => (
            <article key={title} className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-blue-200 hover:shadow-lg hover:shadow-blue-900/5">
              <div className="mb-8 flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600 ring-1 ring-blue-100 transition group-hover:bg-blue-600 group-hover:text-white">
                <Icon size={20} />
              </div>
              <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.15em] text-slate-300">0{index + 1}</div>
              <h3 className="text-base font-semibold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{desc}</p>
            </article>
          ))}
        </div>

        <div id="how-it-works" className="scroll-mt-24 mt-16 grid overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-50 via-white to-sky-50 md:grid-cols-[0.85fr_1.15fr] sm:mt-20">
          <div className="p-7 sm:p-10">
            <div className="mb-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-blue-700"><Layers3 size={14} /> How it works</div>
            <h3 className="max-w-md text-2xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-3xl">A simple loop that keeps you in control.</h3>
            <p className="mt-4 max-w-md text-sm leading-6 text-slate-600">Start with the outcome you want. Review the working app, then guide the next iteration.</p>
          </div>
          <ol className="grid gap-px bg-blue-100/80 sm:grid-cols-3">
            {[
              ["01", "Describe", "Tell GeneSys what you want to make."],
              ["02", "Build", "The agent plans and updates your project."],
              ["03", "Explore", "See the result and ask for refinements."],
            ].map(([number, title, copy]) => (
              <li key={number} className="bg-white/80 p-6 sm:p-7">
                <span className="text-xs font-bold text-blue-600">{number}</span>
                <h4 className="mt-5 text-sm font-semibold text-slate-900">{title}</h4>
                <p className="mt-2 text-xs leading-5 text-slate-600">{copy}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

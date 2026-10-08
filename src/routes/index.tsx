import { createRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles } from "lucide-react";
import { Route as rootRoute } from "./__root";
import { Features } from "@/components/genesys/features";
import { Footer } from "@/components/genesys/footer";
import { Hero } from "@/components/genesys/Hero";
import { Navbar } from "@/components/genesys/navbar";

function HomePage() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <Navbar />
      <main>
        <Hero />
        <Features />

        <section className="bg-white px-5 py-20 sm:px-8 sm:py-24">
          <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-slate-950 px-7 py-12 text-center sm:px-12 sm:py-16">
            <div className="pointer-events-none absolute -right-20 -top-36 h-80 w-80 rounded-full bg-blue-600/30 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-44 -left-10 h-80 w-80 rounded-full bg-sky-500/20 blur-3xl" />
            <div className="relative mx-auto max-w-2xl">
              <div className="mx-auto mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-blue-300 ring-1 ring-white/10">
                <Sparkles size={20} />
              </div>
              <h2 className="text-3xl font-semibold tracking-[-0.045em] text-white sm:text-4xl">
                Your next idea could be your next app.
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
                Start with a description. GeneSys will help turn it into a project you can explore and keep improving.
              </p>
              <Link to="/build" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-blue-700 no-underline shadow-lg shadow-black/10 transition hover:-translate-y-0.5 hover:bg-blue-50">
                Start building <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomePage,
});

import { createRoute, Link } from '@tanstack/react-router'
import { Route as rootRoute } from './__root';
import React from 'react';
import { Navbar } from '@/components/genesys/navbar';
import { Footer } from '@/components/genesys/footer';
import { ArrowRight, Check, Zap, Crown } from 'lucide-react';

function PricingPage() {
  const plans = [
    {
      name: "Free",
      price: "0",
      desc: "For individual experimenters.",
      icon: Zap,
      features: ["5 Daily AI Builds", "Local File Saving", "Community Support", "Basic Preview"],
      cta: "Start Building",
      highlight: false
    },
    {
      name: "Architect Pro",
      price: "25",
      desc: "For serious software builders.",
      icon: Crown,
      features: ["Unlimited Daily Builds", "120b High-Logic Council", "Cloud Deployment Ready", "Priority Support", "Project History"],
      cta: "Upgrade to Pro",
      highlight: true
    }
  ];

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-blue-500/30">
      <Navbar />
      
      <main className="px-5 pb-24 pt-16 sm:px-8 sm:pt-20">
        <div className="mx-auto mb-14 max-w-3xl text-center sm:mb-16">
          <div className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-blue-600">Straightforward plans</div>
          <h1 className="mb-5 text-4xl font-semibold tracking-[-0.05em] text-slate-950 sm:text-6xl">
            Find your way to <span className="text-blue-600">build.</span>
          </h1>
          <p className="mx-auto max-w-xl text-base leading-7 text-slate-600 sm:text-lg">
            Start exploring GeneSys, then choose the plan that fits the way you work.
          </p>
        </div>

        <div className="mx-auto grid max-w-4xl gap-5 md:grid-cols-2">
          {plans.map((p) => (
            <div key={p.name} className={`relative overflow-hidden rounded-3xl border bg-white p-7 shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg sm:p-9 ${p.highlight ? 'border-blue-300 ring-4 ring-blue-50' : 'border-slate-200'}`}>
              {p.highlight && (
                <div className="absolute right-6 top-6 rounded-full bg-blue-50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 ring-1 ring-blue-100">
                  Popular
                </div>
              )}
              
              <div className="mb-7 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 ring-1 ring-blue-100">
                <p.icon size={23} />
              </div>

              <h3 className="mb-2 text-xl font-semibold text-slate-950">{p.name}</h3>
              <p className="mb-8 text-sm text-slate-600">{p.desc}</p>
              
              <div className="mb-8 flex items-baseline gap-1.5">
                <span className="text-5xl font-semibold tracking-tight text-slate-950">${p.price}</span>
                <span className="text-sm text-slate-500">/ month</span>
              </div>

              <ul className="mb-9 space-y-3.5 border-t border-slate-100 pt-6">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-3 text-sm text-slate-600">
                    <Check className="shrink-0 text-blue-600" size={16} /> {f}
                  </li>
                ))}
              </ul>

              {p.highlight ? (
                <button type="button" disabled className="w-full cursor-not-allowed rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-400" title="Plan upgrades are not available yet">{p.cta} · coming soon</button>
              ) : (
                <Link to="/build" className="glow-button flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold no-underline transition hover:-translate-y-0.5">{p.cta} <ArrowRight size={16} /></Link>
              )}
            </div>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}


export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/pricing",
  component: PricingPage,
});

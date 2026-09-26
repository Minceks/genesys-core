import { createRoute } from '@tanstack/react-router';
import { Route as rootRoute } from './__root';
import React from 'react';
import { Navbar } from '@/components/genesys/navbar';
import { Footer } from '@/components/genesys/footer';
import { Check, Zap, Shield, Crown } from 'lucide-react';

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
      
      <main className="pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center mb-20">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-6" style={{ fontFamily: 'Sora' }}>
            System <span className="text-blue-500">Access</span>
          </h1>
          <p className="text-white/40 max-w-xl mx-auto text-lg leading-relaxed">
            Choose your level of integration with the Genesys System Core.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {plans.map((p, i) => (
            <div key={i} className={`p-10 rounded-[2.5rem] border ${p.highlight ? 'border-blue-500 bg-blue-500/5 shadow-[0_0_50px_rgba(59,130,246,0.1)]' : 'border-white/10 bg-white/2'} relative overflow-hidden transition-all hover:scale-[1.02]`}>
              {p.highlight && (
                <div className="absolute top-6 right-6 px-3 py-1 bg-blue-500 text-black text-[10px] font-black uppercase tracking-widest rounded-full">
                  Recommended
                </div>
              )}
              
              <div className="mb-8 p-3 w-fit rounded-2xl bg-white/5 border border-white/10">
                <p.icon className={p.highlight ? 'text-blue-400' : 'text-white/40'} size={28} />
              </div>

              <h3 className="text-2xl font-bold text-white mb-2">{p.name}</h3>
              <p className="text-white/40 text-sm mb-8">{p.desc}</p>
              
              <div className="flex items-baseline gap-1 mb-10">
                <span className="text-6xl font-bold text-white">${p.price}</span>
                <span className="text-white/20 font-bold uppercase text-xs tracking-widest">/ month</span>
              </div>

              <ul className="space-y-4 mb-12">
                {p.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-3 text-white/70 text-sm">
                    <Check className="text-blue-500" size={16} /> {f}
                  </li>
                ))}
              </ul>

              <button className={`w-full py-4 rounded-2xl font-bold transition-all ${p.highlight ? 'glow-button text-black' : 'bg-white/10 text-white hover:bg-white/20'}`}>
                {p.cta}
              </button>
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
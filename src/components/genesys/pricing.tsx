import React from 'react';
import { Check } from 'lucide-react';
import { Link } from '@tanstack/react-router';

export function Pricing() {
  const plans = [
    { name: "Free", price: "0", features: ["5 Daily Builds", "Local Saving"], cta: "Launch Core" },
    { name: "Pro", price: "25", features: ["Unlimited Builds", "120b logic"], cta: "Launch Core", highlight: true }
  ];

  return (
    <section id="pricing" className="py-24 bg-black">
      <div className="max-w-5xl mx-auto px-6 grid md:grid-cols-2 gap-8">
        {plans.map((p, i) => (
          <div key={i} className={`p-10 rounded-[2.5rem] border ${p.highlight ? 'border-blue-500 bg-blue-500/5' : 'border-white/10'}`}>
            <h3 className="text-2xl font-bold text-white mb-2">{p.name}</h3>
            <div className="text-5xl font-bold text-white mb-8">${p.price}</div>
            <ul className="space-y-4 mb-10 text-white/60">
              {p.features.map((f, j) => <li key={j} className="flex items-center gap-2"><Check size={16}/> {f}</li>)}
            </ul>
            <Link to="/build" className={`block text-center py-4 rounded-2xl font-bold no-underline ${p.highlight ? 'bg-blue-600 text-white' : 'bg-white/10 text-white'}`}>
              {p.cta}
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
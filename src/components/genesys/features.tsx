import React from 'react';
import { Zap, Shield, Layout, Cpu, Globe, Code } from 'lucide-react';

const featureList = [
  { title: "Autonomous Building", desc: "Genesys plans and writes full-stack code from a single prompt.", icon: Cpu },
  { title: "Instant Simulation", desc: "Watch your app come to life in the real-time sandbox window.", icon: Zap },
  { title: "Zero Lock-in", desc: "Export clean, production-ready code to your local disk instantly.", icon: Code },
  { title: "Enterprise Security", desc: "Built-in auth and database protection for every system.", icon: Shield },
];

export function Features() {
  return (
    <section id="features" className="py-24 bg-background">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold tracking-tight text-white sm:text-5xl" style={{ fontFamily: 'Sora' }}>
            Powered by the <span className="text-blue-500">Council</span>
          </h2>
          <p className="mt-4 text-white/40 max-w-2xl mx-auto">
            Our multi-agent orchestration ensures every line of code is optimized for performance and design.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {featureList.map((f, i) => (
            <div key={i} className="group p-8 rounded-3xl border border-white/5 bg-white/5 backdrop-blur-sm hover:border-blue-500/30 transition-all">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <f.icon className="text-blue-400" size={24} />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">{f.title}</h3>
              <p className="text-white/40 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
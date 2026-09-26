import { Link } from "@tanstack/react-router";
import React from 'react';

export function Hero() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden bg-black">
      {/* Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />
      
      <div className="max-w-5xl mx-auto px-6 text-center relative z-10">
        <div className="inline-block px-4 py-1.5 mb-8 border border-blue-500/20 rounded-full bg-blue-500/5 text-sm font-medium text-blue-400 uppercase tracking-widest">
          ✨ Genesys 2.0 Core
        </div>
        
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter mb-8 leading-[0.9]" style={{ fontFamily: 'Sora, sans-serif' }}>
          Build apps by <br />
          <span className="text-gradient-brand text-blue-400">talking to AI.</span>
        </h1>
        
        <p className="text-lg md:text-xl text-white/40 max-w-2xl mx-auto mb-12 leading-relaxed">
          The next evolution of autonomous system intelligence. 
          Describe your vision and watch the system architect the code in real-time.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link 
            to="/build" 
            className="glow-button px-10 py-4 rounded-2xl font-bold text-lg no-underline inline-block bg-blue-600 text-black hover:scale-105 transition-transform"
          >
            Launch Core
          </Link>
          <button className="px-10 py-4 rounded-2xl font-semibold border border-white/10 bg-white/5 backdrop-blur hover:bg-white/10 transition-colors text-white">
            View Showcase
          </button>
        </div>
      </div>
    </section>
  );
}
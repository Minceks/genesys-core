import React from 'react';

export function Footer() {
  return (
    <footer className="py-12 border-t border-white/5 text-center">
      <p className="text-xs font-bold tracking-[0.3em] text-white/20 uppercase">
        Genesys AI — Independent System Core
      </p>
      <div className="mt-4 flex justify-center gap-8 text-xs text-white/40 font-bold uppercase tracking-widest">
        <a href="#" className="hover:text-blue-400 transition-colors">Privacy</a>
        <a href="#" className="hover:text-blue-400 transition-colors">Terms</a>
        <a href="#" className="hover:text-blue-400 transition-colors">Twitter</a>
      </div>
    </footer>
  );
}
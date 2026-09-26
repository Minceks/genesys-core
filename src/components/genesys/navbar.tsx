import { Link } from "@tanstack/react-router";
import React from "react";
import { Menu, X, Cpu } from "lucide-react";

export function Navbar() {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <nav className="fixed top-0 z-50 w-full border-b border-white/5 bg-black/60 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* LOGO */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="p-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg group-hover:border-blue-500/50 transition-all">
            <Cpu className="text-blue-400" size={20} />
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-white">
            GENESYS<span className="text-blue-500"> AI</span>
          </span>
        </Link>

        {/* LINKS (Desktop) */}
        <div className="hidden md:flex items-center gap-8 text-xs font-bold uppercase tracking-widest text-white/40">
          <a href="#features" className="hover:text-blue-400 transition-colors">Features</a>
          <a href="#how" className="hover:text-blue-400 transition-colors">Process</a>
          <Link to="/pricing" className="hover:text-blue-400 transition-colors">Pricing</Link>
        </div>

        {/* ACTIONS */}
        <div className="flex items-center gap-4">
          <Link to="/auth" className="hidden sm:block text-xs font-bold uppercase tracking-widest text-white/60 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link 
            to="/build" 
            className="glow-button px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-widest no-underline"
          >
            Launch Builder
          </Link>
          
          {/* Mobile Toggle */}
          <button className="md:hidden text-white" onClick={() => setIsOpen(!isOpen)}>
            {isOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* MOBILE MENU */}
      {isOpen && (
        <div className="md:hidden bg-black border-b border-white/10 p-6 flex flex-col gap-4 animate-in fade-in slide-in-from-top-4">
          <a href="#features" className="text-sm font-bold text-white/60">Features</a>
          <Link to="/pricing" className="text-sm font-bold text-white/60">Pricing</Link>
          <Link to="/auth" className="text-sm font-bold text-white/60">Sign In</Link>
        </div>
      )}
    </nav>
  );
}
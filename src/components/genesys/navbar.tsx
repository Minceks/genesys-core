import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { Menu, X, Layers, ArrowUpRight } from 'lucide-react';

export function Navbar() {
 const [isOpen,setIsOpen]=useState(false);
 return <nav aria-label="Site navigation" className="genesys-navbar">
  <div className="genesys-navbar-inner">
   <Link to="/" className="home-brand" aria-label="Genesys home"><span className="home-mark"><Layers size={18}/></span>Genesys<span className="brand-dot">.</span></Link>
   <div className="genesys-navbar-links"><a href="/#possibilities">Explore</a><a href="/#how-it-works">How it works</a><Link to="/pricing">Pricing</Link></div>
   <div className="genesys-navbar-actions"><Link to="/auth" className="nav-signin">Sign in</Link><Link to="/account" className="home-button">Open builder <ArrowUpRight size={15}/></Link><button type="button" aria-label={isOpen?'Close navigation':'Open navigation'} aria-expanded={isOpen} aria-controls="mobile-navigation" className="nav-menu-toggle" onClick={()=>setIsOpen(!isOpen)}>{isOpen?<X size={20}/>:<Menu size={20}/>}</button></div>
  </div>
  {isOpen&&<div id="mobile-navigation" className="genesys-mobile-nav" onClick={()=>setIsOpen(false)}><a href="/#possibilities">Explore</a><a href="/#how-it-works">How it works</a><Link to="/pricing">Pricing</Link><Link to="/auth">Sign in</Link><Link to="/account">Your projects</Link></div>}
 </nav>;
}

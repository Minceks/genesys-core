import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { ArrowRight, Menu, X } from 'lucide-react'
import { Brand } from './brand'

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  return (
    <header className="g-nav">
      <nav aria-label="Site navigation" className="g-container">
        <div className="g-nav-inner">
          <Brand />
          <div className="g-nav-links">
            <a href="/#ideas">Ideas</a>
            <a href="/#features">Features</a>
            <a href="/#how-it-works">How it works</a>
            <Link to="/pricing">Pricing</Link>
          </div>
          <div className="g-nav-actions">
            <Link to="/auth" className="g-btn g-btn-ghost g-btn-sm g-nav-signin">Sign in</Link>
            <Link to="/account" className="g-btn g-btn-primary g-btn-sm">Start building <ArrowRight size={15} /></Link>
            <button type="button" aria-label={isOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={isOpen} aria-controls="mobile-navigation" className="g-btn g-btn-ghost g-btn-icon g-nav-toggle" onClick={() => setIsOpen(!isOpen)}>
              {isOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        {isOpen && (
          <div id="mobile-navigation" className="g-nav-mobile" onClick={() => setIsOpen(false)}>
            <a href="/#ideas">Ideas</a>
            <a href="/#features">Features</a>
            <a href="/#how-it-works">How it works</a>
            <Link to="/pricing">Pricing</Link>
            <Link to="/auth">Sign in</Link>
            <Link to="/account">Your projects</Link>
          </div>
        )}
      </nav>
    </header>
  )
}

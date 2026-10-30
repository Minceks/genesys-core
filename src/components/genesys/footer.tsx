import { Link } from '@tanstack/react-router'
import { Brand } from './brand'

export function Footer() {
  return (
    <footer className="g-footer">
      <div className="g-container g-footer-inner">
        <Brand size={24} />
        <p className="m-0">Describe it. Build it. Check it. Publish it.</p>
        <nav aria-label="Footer">
          <Link to="/pricing">Pricing</Link>
          <Link to="/terms">Terms</Link>
          <Link to="/account">Your projects</Link>
        </nav>
      </div>
    </footer>
  )
}

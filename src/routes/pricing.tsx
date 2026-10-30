import { createRoute, Link } from '@tanstack/react-router'
import { ArrowRight, Check } from 'lucide-react'
import { Route as rootRoute } from './__root'
import { Navbar } from '@/components/genesys/navbar'
import { Footer } from '@/components/genesys/footer'

export const Route = createRoute({ getParentRoute: () => rootRoute, path: '/pricing', component: Pricing })

function Pricing() {
  return (
    <div className="g-page g-glow flex flex-col">
      <Navbar />
      <main className="g-container flex-1 py-16 sm:py-24">
        <section className="mx-auto max-w-2xl text-center">
          <p className="g-eyebrow">Pricing</p>
          <h1 className="mt-3 text-4xl font-extrabold sm:text-5xl">Build first. Billing comes later.</h1>
          <p className="mt-5 text-lg text-[var(--muted)]">Paid plans and payment processing are not available yet. There is no upgrade checkout on this site.</p>
        </section>
        <section className="g-card mx-auto mt-10 max-w-xl p-6 sm:p-8">
          <h2 className="m-0 text-lg font-bold">What this means today</h2>
          <ul className="mt-4 mb-0 grid list-none gap-3 p-0 text-[var(--muted)]">
            {['Build availability depends on your account allowance.', 'You can view your projects and keep working in your workspace.'].map(item => <li key={item} className="flex gap-3"><Check size={18} className="mt-0.5 shrink-0 text-[var(--success)]" />{item}</li>)}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/account" className="g-btn g-btn-primary">Open your workspace <ArrowRight size={16} /></Link>
            <Link to="/" className="g-btn g-btn-secondary">Back to home</Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}

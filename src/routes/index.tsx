import { useState } from 'react'
import { createRoute, Link } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import { ArrowRight, ArrowUpRight, CalendarCheck, Check, History, LayoutDashboard, MousePointerClick, Palette, Rocket, ScanEye, ShoppingBag, Sparkles, Database, Smartphone } from 'lucide-react'
import { Navbar } from '@/components/genesys/navbar'
import { Footer } from '@/components/genesys/footer'

export const Route = createRoute({ getParentRoute: () => rootRoute, path: '/', component: HomePage })

const ideas = [
  { kind: 'store', icon: ShoppingBag, label: 'Online store', detail: 'Products, details, cart and checkout flow.',
    prompt: 'Build a polished independent stationery store with generous product imagery, product details, a persistent cart and local checkout. Payments come later.' },
  { kind: 'portfolio', icon: Palette, label: 'Creative portfolio', detail: 'Striking work, projects and a contact page.',
    prompt: 'Build an editorial illustrator portfolio with striking original artwork, project details, category filters and a contact section.' },
  { kind: 'booking', icon: CalendarCheck, label: 'Booking app', detail: 'Services, time slots and saved appointments.',
    prompt: 'Build a refined appointment app with service discovery, booking, validation, saved appointments and in-page cancellation.' },
  { kind: 'dashboard', icon: LayoutDashboard, label: 'Team dashboard', detail: 'Tasks, filters, charts and saved data.',
    prompt: 'Build a focused team task dashboard with useful navigation, create and edit forms, filters, completion and persistent local data.' },
]

const features = [
  { icon: Smartphone, title: 'Live preview on desktop and phone', text: 'Watch your project take shape and switch between screen sizes while you work.' },
  { icon: MousePointerClick, title: 'Point at what to change', text: 'Select an element in the preview, then describe the change in plain words.' },
  { icon: History, title: 'Version history', text: 'Restore an earlier build at any time. Your current source is backed up first.' },
  { icon: Database, title: 'Connect a real backend', text: 'Link your own Supabase project for database, sign-in and storage.' },
  { icon: Rocket, title: 'Publish when it is ready', text: 'Review the release checks, then publish a verified version to its own address.' },
]

function HomePage() {
  const [idea, setIdea] = useState('')
  const [notice, setNotice] = useState('')
  function start(event: React.FormEvent) {
    event.preventDefault()
    if (!idea.trim()) return
    try { sessionStorage.setItem('genesys_starter_prompt', idea.trim()); window.location.assign('/account') }
    catch { setNotice('Your browser could not save this idea. Open the builder and paste it into your project.') }
  }
  function choose(prompt: string, scroll = false) {
    setIdea(prompt)
    const field = document.getElementById('project-idea')
    if (scroll) field?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'center' })
    field?.focus({ preventScroll: scroll })
  }
  return (
    <div className="g-page g-glow">
      <Navbar />
      <main>
        <section className="hx-hero g-container">
          <p className="hx-pill"><Sparkles size={14} /> AI that builds it, then checks that it works</p>
          <h1>Turn your idea into a <span className="g-gradient-text">working app</span></h1>
          <p className="hx-lead">Describe a website or application. GeneSys builds it, tests it in a real browser and shows you exactly what passed.</p>
          <form className="hx-composer" onSubmit={start}>
            <label htmlFor="project-idea" className="sr-only">Describe your project</label>
            <textarea id="project-idea" value={idea} onChange={event => setIdea(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) start(event) }} placeholder="A website for my studio, with a gallery and online booking…" rows={3} maxLength={8000} required />
            <div className="hx-composer-row">
              <span><Sparkles size={14} /> The more detail, the better the first build</span>
              <button type="submit" className="g-btn g-btn-primary" aria-label="Start building your idea" disabled={!idea.trim()}>Build it <ArrowRight size={16} /></button>
            </div>
          </form>
          {notice && <p role="status" className="g-notice" style={{ maxWidth: 760, margin: '14px auto 0' }}>{notice}</p>}
          <div className="hx-chips" aria-label="Project ideas">
            {ideas.map(item => <button type="button" key={item.kind} onClick={() => choose(item.prompt)}><item.icon size={14} />{item.label}</button>)}
          </div>
          <div className="hx-demo" aria-hidden="true">
            <div className="hx-demo-bar"><i /><i /><i /><b>GeneSys builder</b></div>
            <div className="hx-demo-body">
              <div className="hx-demo-chat">
                <p className="hx-demo-user">Build a booking site for a dental clinic</p>
                <p className="hx-demo-bot">Done. The site has services, live time slots and a confirmation step.</p>
                <div className="hx-demo-checks">
                  <span><Check size={13} /> Build passed</span>
                  <span><Check size={13} /> Booking flow tested in a browser</span>
                  <span><Check size={13} /> Desktop and phone layouts checked</span>
                </div>
              </div>
              <div className="hx-demo-site">
                <div className="hx-site">
                  <div className="hx-site-nav"><span>Brightline Dental</span><em>Book a visit</em></div>
                  <div className="hx-site-hero">
                    <div><h4>Care that fits around your week</h4><p>Pick a time in under a minute.</p><span className="hx-site-cta">Book now</span></div>
                    <div className="hx-site-card"><strong>Choose your slot</strong><div className="hx-slots"><span>09:00</span><span>10:30</span><span>14:15</span></div></div>
                  </div>
                  <div className="hx-site-row"><div /><div /><div /></div>
                </div>
              </div>
            </div>
          </div>
          <p className="hx-caption">Illustration of the builder. Your project gets its own design and content.</p>
        </section>

        <section id="ideas" className="hx-section g-container">
          <div className="hx-heading">
            <p className="g-eyebrow">Start from an idea</p>
            <h2>Pick a starting point, then make it yours</h2>
          </div>
          <div className="hx-ideas">
            {ideas.map(item => (
              <button type="button" key={item.kind} className="g-card hx-idea" onClick={() => choose(item.prompt, true)} aria-label={`Use the ${item.label} idea`}>
                <span className={`hx-idea-art hx-idea-${item.kind}`}><item.icon size={36} strokeWidth={1.6} /></span>
                <span className="hx-idea-copy"><strong>{item.label}<ArrowUpRight size={16} /></strong><span>{item.detail}</span></span>
              </button>
            ))}
          </div>
        </section>

        <section id="features" className="hx-section hx-section-alt">
          <div className="g-container">
            <div className="hx-heading">
              <p className="g-eyebrow">Built to be trusted</p>
              <h2>More than a good-looking first draft</h2>
              <p>Every build is compiled and tested, and you can see what was checked.</p>
            </div>
            <div className="hx-features">
              <article className="g-card hx-feature hx-feature-wide">
                <span className="hx-feature-icon"><ScanEye size={20} /></span>
                <h3>Tested in a real browser</h3>
                <p>GeneSys clicks through your app, fills in its forms and reviews desktop and phone screenshots. If something fails, it repairs it and tries again.</p>
                <div className="hx-checks">{['Build', 'User journeys', 'Phone layout', 'Visual review'].map(item => <span key={item}><Check size={12} />{item}</span>)}</div>
              </article>
              {features.map(item => (
                <article key={item.title} className="g-card hx-feature">
                  <span className="hx-feature-icon"><item.icon size={20} /></span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="hx-section g-container">
          <div className="hx-heading">
            <p className="g-eyebrow">How it works</p>
            <h2>From first thought to published site</h2>
          </div>
          <div className="hx-steps">
            {[['1', 'Describe it', 'Say who it is for, what it should do and how it should feel. Plan first if you want to think it through.'],
              ['2', 'Build and refine', 'See a live preview, then keep chatting or point at the part you want changed.'],
              ['3', 'Check and publish', 'Review what passed, what needs attention, and publish when you are happy.']].map(([step, title, copy]) => (
              <article key={step}><span>Step {step}</span><h3>{title}</h3><p>{copy}</p></article>
            ))}
          </div>
        </section>

        <section className="g-container" style={{ paddingBottom: 72 }}>
          <div className="g-card hx-cta">
            <h2>Ready to build something?</h2>
            <p>Your first idea is one sentence away.</p>
            <Link to="/account" className="g-btn g-btn-primary g-btn-lg">Start building <ArrowRight size={17} /></Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}

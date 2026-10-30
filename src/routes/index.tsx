import { useState } from 'react'
import { createRoute, Link } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
import { ArrowUpRight, ArrowRight, Layers, Check, Sparkles } from 'lucide-react'
export const Route = createRoute({ getParentRoute: () => rootRoute, path: '/', component: HomePage })
const ideas = [
 ['A beautiful storefront','Build a polished independent stationery store with generous product imagery, product details, a persistent cart and local checkout. Payments come later.'],
 ['My creative portfolio','Build an editorial illustrator portfolio with striking original artwork, project details, category filters and a contact section.'],
 ['An appointment app','Build a refined appointment app with service discovery, booking, validation, saved appointments and in-page cancellation.'],
 ['A team dashboard','Build a focused team task dashboard with useful navigation, create and edit forms, filters, completion and persistent local data.'],
]
function HomePage() {
 const [idea,setIdea]=useState('')
 const [notice,setNotice]=useState('')
 function start(event: React.FormEvent) {
  event.preventDefault()
  if(!idea.trim()) return
  try {sessionStorage.setItem('genesys_starter_prompt',idea.trim());window.location.assign('/account')}
  catch {setNotice('Your browser could not save this idea. Open the builder and paste it into your project.')}
 }
 function choose(prompt:string,scroll=false){setIdea(prompt);const field=document.getElementById('project-idea');if(scroll)field?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});field?.focus({preventScroll:scroll})}
 return <div className="genesys-home">
  <header className="home-header"><nav aria-label="Main navigation" className="home-container home-nav">
   <Link to="/" aria-label="Genesys home" className="home-brand"><span className="home-mark"><Layers size={20}/></span>Genesys<span className="brand-dot">.</span></Link>
   <div className="home-nav-links"><a href="#possibilities">Explore</a><a href="#how-it-works">How it works</a></div>
   <div className="home-nav-actions"><Link to="/auth">Sign in</Link><Link to="/account" className="home-button home-button-small">Open builder <ArrowUpRight size={15}/></Link></div>
  </nav></header>
  <main>
   <section className="home-hero home-container">
    <p className="home-eyebrow"><span/> An independent space for your next idea</p>
    <h1>What will you<br/><span>bring to life?</span></h1>
    <p className="home-intro">Turn a thought into a website or app.<br className="home-desktop-break"/> Build with AI. Refine the details. Make it yours.</p>
    <form className="idea-composer" onSubmit={start}><label htmlFor="project-idea" className="sr-only">Describe your project</label>
     <textarea id="project-idea" value={idea} onChange={event=>setIdea(event.target.value)} placeholder="A website for my studio, with a gallery and booking…" rows={3} maxLength={8000} required/>
     <div className="composer-bottom"><span><Sparkles size={15}/> Start with an idea, not a blank canvas.</span><button type="submit" aria-label="Start building your idea" disabled={!idea.trim()}><ArrowRight size={20}/></button></div>
    </form>
    {notice&&<p role="status">{notice}</p>}
    <div className="idea-suggestions" aria-label="Project ideas">{ideas.map(([label,prompt])=><button type="button" key={label} onClick={()=>choose(prompt)}>{label}<ArrowUpRight size={13}/></button>)}</div>
    <p className="home-fineprint">Plan first, build together, and see what was checked.</p>
   </section>
   <section id="possibilities" className="home-container home-explore">
    <div className="home-section-heading"><div><p className="home-eyebrow">A starting point, made yours</p><h2>Different ideas.<br/>Distinctive directions.</h2></div><p>Stores, portfolios and everyday tools.<br/>Your project should feel like your project.</p></div>
    <div className="direction-grid">{[
     ['studio','01 / Creative portfolio','Room for your work to speak.','FIELDNOTES','Selected work — 2026'],
     ['store','02 / Independent commerce','A considered home for your products.','FORM & FIELD','Objects for a slower everyday.'],
     ['workspace','03 / Useful applications','Less friction. More getting things done.','Monday studio','A little clarity for your day.'],
    ].map(([kind,category,title,name,subtitle],index)=><button key={kind} type="button" className={`direction-card direction-${kind}`} onClick={()=>choose(ideas[index===0?1:index===1?0:3][1],true)} aria-label={`Use ${category.slice(5)} idea`}>
     <div className="direction-art" aria-hidden="true"><div className="mini-nav">{name}<span>•••</span></div><div className="mini-title">{subtitle}</div>{kind==='studio'?<div className="mini-gallery"><div/><div/></div>:kind==='store'?<div className="mini-products"><div/><div/><div/></div>:<div className="mini-tasks">{['Review the first concepts','Make room for the good ideas','Bring the details together'].map((text,i)=><div key={text}><span className={i===0?'done':''}/>{text}<i/></div>)}</div>}</div>
     <div className="direction-caption"><p>{category}</p><h3>{title}<ArrowUpRight size={17}/></h3></div>
    </button>)}</div><p className="home-fineprint">Original illustrative design directions. Your generated project will have its own content and layout.</p>
   </section>
   <section id="how-it-works" className="home-process"><div className="home-container"><div className="home-section-heading"><div><p className="home-eyebrow">From first thought to finer details</p><h2>A conversation.<br/>A clearer way to create.</h2></div><Link to="/account" className="home-text-link">Start your project <ArrowUpRight size={17}/></Link></div>
    <div className="process-grid">{[['01','Describe the idea','Tell Genesys who it is for, what it should do, and how it should feel.'],['02','Build and explore','Move between your conversation and preview. Review the plan before making changes.'],['03','Refine with confidence','Check desktop and phone layouts, review functional results, and keep improving.']].map(([step,title,copy])=><article key={step}><span>{step}</span><h3>{title}</h3><p>{copy}</p></article>)}</div>
    <div className="home-assurance"><Check size={17}/><p>Functional checks, visual review and deferred integrations are shown separately. See what is ready and what still needs attention.</p></div>
   </div></section>
  </main>
  <footer className="home-container home-footer"><Link to="/" className="home-brand"><Layers size={18}/>Genesys.</Link><p>Independent tools. Ideas of your own.</p><Link to="/account">Your workspace <ArrowUpRight size={15}/></Link></footer>
 </div>
}

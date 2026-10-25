"""Passive, bounded reference structure; never recover form values or secrets."""

STRUCTURE_SCRIPT = """() => {
 const label=e=>(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,80);
 const destination=e=>{try{const u=new URL(e.getAttribute('href'),location.href);
   return ['http:','https:'].includes(u.protocol)&&u.origin===location.origin?u.pathname:null;
 }catch{return null}};
 return {
  destinations:[...document.querySelectorAll('header a[href],nav a[href],main a[href]')].slice(0,60)
    .map(e=>({label:label(e),path:destination(e)})).filter(e=>e.path).slice(0,20),
  forms:[...document.forms].slice(0,4).map(f=>({
    fields:[...f.querySelectorAll('input,select,textarea')].filter(e=>!['hidden','password'].includes(e.type)).slice(0,12)
      .map(e=>({tag:e.tagName.toLowerCase(),type:e.type||e.tagName.toLowerCase(),required:e.required,
        label:(e.getAttribute('aria-label')||(e.labels&&e.labels[0]?.textContent)||'').trim().slice(0,80)})),
    submitPresent:!!f.querySelector('button:not([type]),button[type="submit"],input[type="submit"]')
  })),
  disclosures:[...document.querySelectorAll('details,button[aria-expanded],[role="tab"]')].slice(0,12)
    .map(e=>({kind:e.tagName==='DETAILS'?'details':e.getAttribute('role')||'disclosure',
      label:e.tagName==='DETAILS'?label(e.querySelector('summary')||e):label(e),
      expanded:e.tagName==='DETAILS'?e.open:e.getAttribute('aria-expanded')}))
 };
}"""


def structure_handoff(viewports):
    """Retain evidence per viewport; differences do not imply missing features."""
    return {
        'viewports': [{'viewport': view.get('viewport'),
                       'structure': view.get('interactionStructure') or {}}
                      for view in viewports[:2]],
        'scope': 'Passive DOM structure only. Links were not followed and forms were not submitted. Required attributes are observed declarations, not tested validation or backend delivery.',
        'adaptation': 'Use relevant destinations, form grouping and disclosure hierarchy to plan complete original journeys within the user request. Do not copy text, private data or brand assets. Never add every observed feature automatically. Verify implemented navigation, direct reload, validation, result and recovery states in the generated app.',
    }

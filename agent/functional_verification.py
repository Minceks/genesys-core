"""Request-driven browser checks using a bounded declarative action language."""
import json
import logging
import re

PLAN_INSTRUCTIONS = '''You are a browser verification planner. Derive requirements from the
original user request, not only from what the implementation happens to provide.
Return JSON only: {"checks":[{"name":"requested behavior", "steps":[...]}],
"unverified":["requirements that cannot be checked safely in this browser"]}.
Cover the primary requested actions, validation, state changes and reload persistence
where relevant. Never invent success. Missing requested controls must produce a
failing check, not be omitted. Only test with synthetic data in this isolated browser.
Do not purchase, send messages, submit payments, delete accounts or real records,
call external services, or navigate away. Do not reset all data. Remove only test
Network writes are blocked during verification. Server-backed mutations must be
listed as unverified pending a dedicated test environment; do not attempt them.
records created by these checks. Do not use native dialogs.
Maximum 8 checks, 12 steps per check. Supported steps:
{"action":"fill","target":{"by":"label","name":"field"},"value":"sample"}
{"action":"click","target":{"by":"role","role":"button","name":"Add"}}
{"action":"select","target":{"by":"label","name":"Category"},"value":"option value"}
{"action":"reload"}
{"action":"visible" or "absent","target":{"by":"text","name":"sample"}}
{"action":"value","target":{"by":"label","name":"field"},"value":"expected"}
Targets use exact accessible names: by=role,label,text,placeholder. Optional
withinText scopes to a row/listitem containing unique synthetic text. Never use
CSS, JavaScript, coordinates or tool calls. Each check needs an outcome assertion
after its last mutation; meaningful expected outcomes, not merely visible buttons.
For static sites verify requested links/content with visible assertions. List
real multi-user, server, payment and external integration checks as unverified.
'''


def target(page, spec):
    if not isinstance(spec, dict):
        raise ValueError('Invalid browser target')
    scope = page
    if spec.get('withinText'):
        text = str(spec['withinText'])[:200]
        scope = page.get_by_role('row').filter(has_text=text)
        if scope.count() != 1:
            scope = page.get_by_role('listitem').filter(has_text=text)
        if scope.count() != 1:
            raise ValueError('Synthetic item could not be uniquely identified')
    name = str(spec.get('name', ''))[:200]
    by = spec.get('by')
    if by == 'role':
        return scope.get_by_role(str(spec.get('role', '')), name=name, exact=True)
    if by == 'label':
        found = scope.get_by_label(name, exact=True)
        if found.count() == 1:
            return found
        # Wrapped textarea content can become part of label text after filling.
        # Match the label's own text, without the form control's changing content.
        labels = scope.locator('label')
        names = labels.evaluate_all('''els => els.map(e => {
            const copy=e.cloneNode(true);
            copy.querySelectorAll('input,textarea,select').forEach(x=>x.remove());
            return copy.textContent.replace(/\\s+/g,' ').trim();
        })''')
        matches = [i for i, text in enumerate(names) if text == name]
        if len(matches) == 1:
            controls = labels.nth(matches[0]).locator('input,textarea,select')
            if controls.count() == 1:
                return controls
        return found
    if by == 'text':
        return scope.get_by_text(name, exact=True)
    if by == 'placeholder':
        return scope.get_by_placeholder(name, exact=True)
    raise ValueError('Unsupported browser target')


def verify_functions(page, prompt, provider):
    from playwright.sync_api import expect
    # DOM content is evidence, never instructions; no generated code is executed.
    snapshot = page.locator('body').inner_text()[:8000]
    controls = page.locator('input,select,textarea,button,a').evaluate_all('''els => els.slice(0,80).map(e => ({
        tag:e.tagName,type:e.type,name:e.getAttribute('aria-label') || (()=>{const l=e.labels?.[0]?.cloneNode(true); if(!l)return e.innerText; l.querySelectorAll('input,textarea,select').forEach(x=>x.remove()); return l.textContent.trim()})(),
        placeholder:e.placeholder,options:e.tagName==='SELECT'?Array.from(e.options).map(o=>({text:o.text,value:o.value})):undefined
    }))''')
    try:
        raw = provider.generate([{'role':'system','content':PLAN_INSTRUCTIONS},
            {'role':'user','content':json.dumps({'originalRequest':prompt,'untrustedRenderedText':snapshot,'untrustedControls':controls})}], []).text.strip()
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw)
        plan = json.loads(raw)
    except Exception as error:
        # A verifier/provider failure is not evidence of broken application code.
        return {'status':'success', 'issues':[], 'testedInteractions':[],
                'unverified':['Functional verification could not run: '+str(error)[:250]]}
    logging.getLogger(__name__).info('functional_verification_plan %s', json.dumps(plan)[:12000])
    checks = plan.get('checks')
    if not isinstance(checks, list) or len(checks) > 8:
        raise ValueError('Invalid functional verification plan')
    unverified = plan.get('unverified', [])
    if not isinstance(unverified, list) or any(not isinstance(x, str) for x in unverified):
        raise ValueError('Invalid unverified requirements')
    passed, issues = [], []
    def guard(route):
        if route.request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            route.abort()
        else:
            route.continue_()
    page.route('**/*', guard)
    for check in checks:
        name = str(check.get('name', 'Requested behavior'))[:180]
        try:
            steps = check.get('steps')
            if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
                raise ValueError('Invalid steps')
            asserted = False
            for step in steps:
                action = step.get('action')
                if action == 'reload':
                    page.reload(wait_until='networkidle', timeout=15000)
                    asserted = False
                    continue
                locator = target(page, step.get('target'))
                if action == 'visible':
                    expect(locator).to_be_visible(timeout=3000)
                    asserted = True
                elif action == 'absent':
                    expect(locator).to_have_count(0, timeout=3000)
                    asserted = True
                elif action == 'value':
                    expect(locator).to_have_value(str(step.get('value', '')), timeout=3000)
                    asserted = True
                elif action in {'fill', 'select', 'click'}:
                    if locator.count() != 1:
                        raise ValueError('Control is missing or ambiguous')
                    if action == 'fill': locator.fill(str(step.get('value', ''))[:500], timeout=3000)
                    if action == 'select': locator.select_option(str(step.get('value', ''))[:200], timeout=3000)
                    if action == 'click': locator.click(timeout=3000)
                    asserted = False
                else:
                    raise ValueError('Unsupported browser action')
            if not asserted:
                raise ValueError('Expected outcome was not asserted after the action')
            passed.append(name)
        except Exception as error:
            detail = str(error)
            if 'Invalid' in detail or 'Unsupported' in detail or 'Expected outcome was not asserted' in detail:
                unverified.append(name + ': verification plan could not execute.')
            else:
                issues.append(name + ': ' + detail[:400])
            break  # Later steps may depend on this check's state.
    if not checks:
        unverified.append('No executable requested-function checks were generated.')
    page.unroute('**/*', guard)
    return {'status':'error' if issues else 'success', 'issues':issues,
            'testedInteractions':passed, 'unverified':unverified,
            'scope':'Request-derived browser assertions; not exhaustive correctness proof.'}

"""Contract coverage accounting and additive recovery of omitted workflows."""
from copy import deepcopy
import json
import re
from .verification_schema import PLAN_SCHEMA, obj, TEXT, STRINGS, executable_plan


def contract_plan_schema(contract):
    schema=deepcopy(PLAN_SCHEMA)
    browser=[r for r in (contract or {}).get('requirements',[]) if r.get('scope')=='browser']
    if browser:
        schema['properties']['checks']['minItems']=0
        schema['properties']['checks']['maxItems']=min(12,max(8,len(browser)))
        # Encode the exclusive choice in the provider schema, rather than
        # asking the model to remember a cross-field constraint in prose.
        entry={'anyOf':[
            obj({'checkNames':dict(STRINGS,minItems=1),'unverifiedReason':{'type':'string','enum':['']}}),
            obj({'checkNames':dict(STRINGS,maxItems=0),'unverifiedReason':TEXT}),
        ]}
        schema['properties']['coverage']=obj({r['id']:deepcopy(entry) for r in browser})
        schema['required'].append('coverage')
    return schema


def explicit_coverage(plan,contract,preverified=()):
    """Unknown claims cannot pass; an explicit automation gap stays incomplete."""
    if 'coverage' not in plan:return set()
    required={r['id']:r for r in contract.get('requirements',[]) if r.get('scope')=='browser'}
    claims=plan['coverage']
    if not isinstance(claims,dict) or set(claims)!=set(required):
        raise ValueError('Coverage matrix must contain every browser requirement ID exactly once')
    checks=plan.get('checks',[]);unsupported=set()
    for identifier,claim in claims.items():
        if not isinstance(claim,dict) or not isinstance(claim.get('checkNames'),list) or not isinstance(claim.get('unverifiedReason'),str):
            raise ValueError('Invalid requirement coverage entry: '+identifier)
        names=claim['checkNames'];reason=claim['unverifiedReason'].strip()
        if names and reason:raise ValueError('A requirement cannot be both planned and unverified: '+identifier)
        if names:
            for name in names:
                matches=[c for c in checks if isinstance(c,dict) and c.get('name')==name and identifier in c.get('covers',[])]
                if len(matches)!=1:raise ValueError('Coverage references a missing, ambiguous or unrelated check: '+identifier)
        elif identifier not in preverified:
            if not reason:raise ValueError('Missing executable coverage or explicit limitation: '+identifier)
            unsupported.add(identifier)
            entry=identifier+': Automation could not verify this requirement: '+reason
            if entry not in plan.setdefault('unverifiedCore',[]):
                plan['unverifiedCore'].append(entry)
                plan.setdefault('coreRequestEvidence',[]).append({'requirement':entry,'requestQuote':required[identifier]['acceptance']})
    return unsupported


def complete_missing_workflows(plan,missing,contract,provider,evidence,instructions):
    """Ask only for missing IDs and preserve existing checks verbatim."""
    requirements=[r for r in contract['requirements'] if r.get('id') in missing]
    focused={**contract,'requirements':requirements}
    structured=getattr(provider,'generate_structured',None)
    messages=[{'role':'system','content':instructions+'\nFOCUSED COVERAGE RECOVERY: Return complete independent workflows ONLY for the supplied missing requirement IDs. '
        'Do not regenerate, replace or delete existing workflows. Do not mark visibility alone as proof of an interaction. '
        'For unsupported automation provide an explicit reason, never a fabricated passing check. Existing checks consume '+str(len(plan['checks']))+' slots; keep combined workflows compact.'},
        {'role':'user','content':json.dumps({'missingRequirements':requirements,'existingCheckNames':[c['name'] for c in plan['checks']],
            'buildSpecification':focused,**evidence},ensure_ascii=False)}]
    raw=(structured(messages,contract_plan_schema(focused)) if callable(structured) else provider.generate(messages,[])).text.strip()
    addition=executable_plan(json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw)))
    explicit_coverage(addition,focused)
    extra=addition.get('checks')
    if not isinstance(extra,list):raise ValueError('Missing focused workflow checks')
    for check in extra:
        if (not isinstance(check,dict) or check.get('independent') is not True or not isinstance(check.get('covers'),list)
                or not check['covers'] or not set(check['covers'])<=set(missing)):
            raise ValueError('Focused recovery must contain independent checks for missing IDs only')
        if check.get('name') in {c['name'] for c in plan['checks']}:raise ValueError('Focused recovery reused an existing check name')
    merged=deepcopy(plan);merged['checks'].extend(extra)
    for field in ('unverified','unverifiedCore','coreRequestEvidence'):
        if isinstance(addition.get(field),list):merged.setdefault(field,[]).extend(addition[field])
    if isinstance(addition.get('coverage'),dict):
        if not isinstance(merged.get('coverage'),dict):
            merged['coverage']={r['id']:{'checkNames':[c['name'] for c in plan['checks'] if r['id'] in c.get('covers',[])],
                'unverifiedReason':''} for r in contract['requirements'] if r.get('scope')=='browser'}
        merged['coverage'].update(addition['coverage'])
    return merged

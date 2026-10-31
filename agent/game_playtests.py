"""Server-owned foundation regressions. Real browser inputs; no game-state hooks."""
import json
from pathlib import Path
from playwright.sync_api import expect

ROOT=Path(__file__).with_name('game_foundations')/'survival'


def foundation_contract(prompt):
    import hashlib
    from .build_spec import PLANNING_POLICY_VERSION
    value=json.loads((ROOT/'contract.json').read_text())
    value.update(version=2,planningPolicyVersion=PLANNING_POLICY_VERSION,
        replacementContractVersion=1,foundationContractVersion=1,
        request=prompt,requestHash=hashlib.sha256(prompt.encode()).hexdigest())
    return value


def supports_contract(contract):
    return (isinstance(contract,dict) and contract.get('foundationContractVersion')==1
            and contract.get('requirements')==json.loads((ROOT/'contract.json').read_text())['requirements'])


def add_edit_checks(result, edit, requirements):
    # Tuning is judged by playing it: the regressions already passed, so a guessed
    # target such as "at least five infected" is reported without failing the build.
    edit.pop('_verifiedPlan',None)
    passed=(edit.get('coverage') or {}).get('passedIds',[])
    result.setdefault('testedInteractions',[]).extend(edit.get('testedInteractions',[]))
    result['coverage']['requirements'].extend(r for r in requirements if r['id'] in passed)
    result['coverage']['passedIds'].extend(passed)
    for r in requirements:
        if r['id'] not in passed:
            result.setdefault('unverified',[]).append('Requested change not confirmed automatically, play it to judge: '+r['name'])
    return result


def verify_foundation(page, prompt, provider, contract, sources, preverified, callback):
    from .functional_verification import verify_functions,restore_verification_state
    from .verification_frames import sample_canvas
    subset=dict(contract,requirements=[r for r in contract['requirements'] if r['id'] not in {'r9-phone-touch','r10-loss-and-retry'}])
    original=page.evaluate('() => ({local:{...localStorage},session:{...sessionStorage}})');original['url']=page.url
    plan=json.loads((ROOT/'browser-plan.json').read_text())
    result=verify_functions(page,prompt,provider,sources=sources,preverified=preverified,contract=subset,
        _plan_override=plan,_repair_round=2,_on_workflow=callback)
    # The native phone/loss checks must always execute; never cache a partial DSL plan.
    result.pop('_verifiedPlan',None)
    if result.get('issues') or result.get('unverifiedCore'):return result
    viewport=page.viewport_size
    cdp=None
    requirement='r9-phone-touch'
    try:
        restore_verification_state(page,original)
        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button',name='Start game',exact=True).click()
        canvas=page.get_by_label('Playfield canvas',exact=True)
        a=page.get_by_label('Movement joystick',exact=True).bounding_box()
        b=page.get_by_role('button',name='Fire weapon',exact=True).bounding_box()
        assert a and b and min(a['width'],a['height'],b['width'],b['height'])>=44,'Phone primary controls must be reachable and >=44px'
        before=sample_canvas(canvas)
        cdp=page.context.new_cdp_session(page)
        cdp.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':2})
        points=[{'id':1,'x':a['x']+a['width']*.75,'y':a['y']+a['height']*.5},
                {'id':2,'x':b['x']+b['width']*.5,'y':b['y']+b['height']*.5}]
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
        page.wait_for_timeout(1800)
        after=sample_canvas(canvas)
        assert sum(abs(x-y)>16 for x,y in zip(before,after))>24,'Concurrent touch must produce rendered action'
        # Lift movement finger while the independent firing pointer stays down.
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[points[1]]})
        expect(page.get_by_label('Score',exact=True)).not_to_have_text('00000',timeout=5000)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        if callback:callback(page,'Rendered action frame: Native dual-touch phone combat')
        page.set_viewport_size({'width':844,'height':390});page.reload(wait_until='networkidle')
        expect(page.get_by_role('button',name='Fire weapon',exact=True)).to_be_visible()
        for control in [page.get_by_role('button',name='Fire weapon',exact=True),page.get_by_label('Movement joystick',exact=True)]:
            bounds=control.bounding_box()
            assert bounds and bounds['x']>=0 and bounds['y']>=0 and bounds['x']+bounds['width']<=844 and bounds['y']+bounds['height']<=390,'Landscape controls must remain on screen'
        result['coverage']['passedIds'].append(requirement)
        result['testedInteractions'].append('Real dual-touch phone movement/fire, independent release and landscape reload')
        requirement='r10-loss-and-retry'
        page.set_viewport_size(viewport);restore_verification_state(page,original)
        page.get_by_role('button',name='Start game',exact=True).click()
        expect(page.get_by_role('heading',name='Signal lost',exact=True)).to_be_visible(timeout=45000)
        page.get_by_role('button',name='Retry level',exact=True).click()
        expect(page.get_by_label('Wave number',exact=True)).to_have_text('1')
        expect(page.get_by_label('Health',exact=True)).to_have_text('5')
        expect(page.get_by_label('Score',exact=True)).to_have_text('00000')
        result['coverage']['passedIds'].append(requirement)
        result['testedInteractions'].append('Natural contact loss and fresh-run retry')
    except Exception as error:
        message=requirement+': '+str(error)[:500]
        result['status']='error';result['issues'].append(message);result['unverifiedCore'].append(message)
    finally:
        if cdp:
            try:
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                cdp.send('Emulation.setTouchEmulationEnabled',{'enabled':False});cdp.detach()
            except Exception:pass
        page.set_viewport_size(viewport)
        restore_verification_state(page,original)
    result['coverage']['requirements']=[r for r in contract['requirements'] if r['scope']=='browser']
    for r in result['coverage']['requirements']:
        if r['id'] not in result['coverage']['passedIds']:
            message=r['id']+': Foundation regression did not complete'
            if not any(str(v).startswith(r['id']+':') for v in result['unverifiedCore']):result['unverifiedCore'].append(message)
    edits=[r for r in contract.get('editRequirements',[]) if r.get('scope')=='browser']
    if edits and not result.get('issues') and not result.get('unverifiedCore'):
        scoped=dict(contract,requirements=edits,editRequirements=[])
        add_edit_checks(result,verify_functions(page,prompt,provider,sources=sources,contract=scoped,_repair_round=2,_on_workflow=callback),edits)
    return result

"""A tested game engine and UI are reusable tools, not per-request manual repairs."""
import json
import re
from pathlib import Path
from .design_quality import BUILD_STANDARD
from .progress import report_progress, model_request_scope


def _object(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def _text(limit):
    return {'type':'string','minLength':1,'maxLength':limit}


COLOR={'type':'string','pattern':r'^#[0-9a-fA-F]{6}$'}
FOUNDATION_SCHEMA=_object({'gameDesign':_object({
    **{k:_text(n) for k,n in [('title',55),('subtitle',65),('eyebrow',65),('description',180),('operation',55),('enemySignal',55)]},
    'brand':{'type':'array','items':_text(14),'minItems':2,'maxItems':2},
    'headline':{'type':'array','items':_text(9),'minItems':3,'maxItems':3},
    'storageKey':{'type':'string','pattern':r'^[a-z][a-z0-9-]{2,40}$'},
    'colors':_object({**{k:COLOR for k in ['accent','background','text','player','enemy']},
        'ground':{'type':'array','items':COLOR,'minItems':5,'maxItems':5}}),
    'balance':_object({'dashCooldown':{'type':'number','minimum':3,'maximum':7},'pulseCooldown':{'type':'number','minimum':8,'maximum':16}}),
    'levels':{'type':'array','minItems':5,'maxItems':5,'items':_object({
        'id':{'type':'integer','minimum':1,'maximum':5},'name':_text(32),'tag':_text(40),'brief':_text(160),'color':COLOR,
        'waves':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'integer','minimum':3,'maximum':16}},
        'speed':{'type':'number','minimum':35,'maximum':86},'layout':{'type':'integer','minimum':0,'maximum':4}})}
}), 'designDecision':_text(700)})


def survival_foundation_fits(prompt, brief):
    if (brief or {}).get('productType') != 'game':
        return False
    text=prompt.casefold()
    if re.search(r'\b(3d|fps|first.person|third.person|platformer|puzzle|chess|card|racing|multiplayer|online|endless.only|minimal|prototype|isometric|strategy|rts|narrative|story|loot|pickups|procedural|inventory|crafting|snow|snowy|frozen|forest|desert|underwater|space|boss|bosses|grenades|rocket|sniper|grapple|building|shop|purchases|platforms)\b',text):
        return False
    if re.search(r'\b\d+\s+(zombies|enemies|waves)\b',text):
        return False
    if re.search(r'\b(no|without)\s+(skills|abilities|shooting)\b',text):
        return False
    if re.search(r'\b([1-46-9]|one|two|three|four|six|seven|eight|nine)\s+(levels|sectors)\b',text):
        return False
    return bool(re.search(r'\bzombie\b',text))


def validate_survival_design(value):
    if not isinstance(value,dict):raise ValueError('Game design must be an object')
    for key,limit in [('title',55),('subtitle',65),('eyebrow',65),('description',180),('operation',55),('enemySignal',55)]:
        if not isinstance(value.get(key),str) or not 1<=len(value[key].strip())<=limit:
            raise ValueError('Invalid game design text: '+key)
    for key,count,limit in [('brand',2,14),('headline',3,9)]:
        if not isinstance(value.get(key),list) or len(value[key])!=count or any(not isinstance(v,str) or not 1<=len(v.strip())<=limit for v in value[key]):
            raise ValueError('Invalid game design '+key)
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,40}',str(value.get('storageKey',''))):
        raise ValueError('Game storage key must be namespaced')
    colors=value.get('colors') or {}
    for key in ['accent','background','text','player','enemy']:
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(colors.get(key,''))):raise ValueError('Invalid game color '+key)
    if not isinstance(colors.get('ground'),list) or len(colors['ground'])!=5 or any(not re.fullmatch(r'#[0-9a-fA-F]{6}',str(v)) for v in colors['ground']):
        raise ValueError('Five scene ground colors are required')
    balance=value.get('balance') or {}
    for key,low,high in [('dashCooldown',3,7),('pulseCooldown',8,16)]:
        if type(balance.get(key)) not in (int,float) or not low<=balance[key]<=high:raise ValueError('Unfair skill cooldown '+key)
    levels=value.get('levels')
    if not isinstance(levels,list) or len(levels)!=5:raise ValueError('This foundation supports five sectors')
    for i,level in enumerate(levels):
        if not isinstance(level,dict) or level.get('id')!=i+1 or type(level.get('layout')) is not int or not 0<=level['layout']<=4:
            raise ValueError('Invalid sector identity/layout')
        if any(not isinstance(level.get(k),str) or not 1<=len(level[k])<=limit for k,limit in [('name',32),('tag',40),('brief',160)]):raise ValueError('Invalid sector content')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(level.get('color',''))):raise ValueError('Invalid sector accent')
        waves=level.get('waves')
        if not isinstance(waves,list) or len(waves)!=2 or any(type(n) is not int or not 3<=n<=min(8+i*2,16) for n in waves):raise ValueError('Unbalanced sector wave counts')
        if type(level.get('speed')) not in (int,float) or not 35<=level['speed']<=min(50+i*9,86):raise ValueError('Unbalanced enemy speed')
    return value


def draft_survival(prompt, source, provider_for, deadline):
    from .parallel_build import parsed
    context=json.loads(source);brief=context['designBrief']
    report_progress('Adapting the tested survival engine, scene art and responsive game interface')
    instruction=BUILD_STANDARD+'''\nGAME PRODUCTION PLAN. GAME FOUNDATION DESIGN. Use the tested survival-v1 foundation.
Return JSON only: {"gameDesign":{...},"designDecision":"why this original direction fits"}.
You are creating the requested game using a real reusable engine and designed UI, not
rewriting its boilerplate. The foundation supplies a detailed top-down world with buildings,
crates/cars, animated recognizable survivors/walkers/runners/brutes, projectiles/hit feedback,
five sectors with two waves each, fair timed damage, dash (E), area pulse (Q), upgrades,
pause/loss/retry, actual sound, reduced motion, phone camera and dual-touch controls,
saved progress, sector selection and direct wave URLs. The world art is an urban/industrial quarantine: service yards, roads, buildings, crates, cars and barricades. Do not promise snow, a frozen landscape, forests, space or other biomes the renderer does not contain. Preserve these working mechanics.
Choose an ORIGINAL name, concise three-line headline, world/mission content, restrained
dark palette, actor colors, sector visual variants, wave balance and cooldowns for this request.
Do not repeat Nightfall/Wave Zombie branding. This is not evidence of current popularity.
gameDesign exact fields:
title (<=55 chars), brand (2 strings <=14 chars each), subtitle (<=65), eyebrow (<=65),
headline (3 strings <=9 chars each), description (<=180), operation (<=55), enemySignal (<=55),
storageKey (3-41 lowercase letters/digits/hyphens, starts with a letter),
colors {accent,background,text,player,enemy,ground:[5 colors]} all #RRGGBB.
Use a dark background/ground, pale readable text/accent and distinct actor colors.
balance {dashCooldown:3..7, pulseCooldown:8..16} seconds.
levels: exactly 5 objects {id:1..5,name:<=32,tag:<=40,brief:<=160,color:#RRGGBB,
waves:[two integer enemy counts],speed:number,layout:0..4}.
The first sector uses the tested onboarding layout 0, waves [4,6] and speed 45; keep its original name/brief/colors, not new mechanics. Later sectors are your difficulty/content progression. Fair wave-count maxima by sector are [8,10,12,14,16], minimum 3. Enemy speed limits
are [50,59,68,77,86], minimum 35. Teach ordinary firing/movement before escalation.
Use purposeful sector names and briefs with actual gameplay context. Honor the supplied
acceptance contract; do not declare required outcomes unsupported or invent approval.
Write short complete English phrases and sentences, never pad to the length limits or end mid-word. Target a description under 110 characters, eyebrow under 35, and headline lines at most 9 characters to keep three deliberate lines on phones. No decorative Unicode. Keep the response compact, under 1100 words. No code, file rewrites or asset URLs.'''
    payload={'request':prompt,'buildSpecification':brief.get('buildSpecification'),
             'visualSystem':brief.get('visualSystem'),
             'observedReferences':(brief.get('referenceAnalysis') or {}).get('visualUnderstanding')}
    provider=provider_for('openai');error=None
    for attempt in range(2):
        with model_request_scope(deadline):
            response=parsed(provider.generate([{'role':'system','content':instruction},
                {'role':'user','content':json.dumps({**payload,'previousValidationError':str(error) if error else None})}],[], response_schema=FOUNDATION_SCHEMA).text)
        try:
            design=validate_survival_design(response.get('gameDesign'))
            # A known teaching encounter is part of the tested runtime contract, not
            # an unbounded model-generated difficulty spike or obstructed spawn layout.
            design['levels'][0].update(waves=[4,6], speed=45, layout=0)
            break
        except ValueError as exc:
            error=exc
            if attempt:raise
    path=Path(__file__).with_name('game_foundations')/'survival'
    files={target:(path/name).read_text(encoding='utf-8') for target,name in {
        'src/App.jsx':'App.jsx','src/projectLogic.js':'projectLogic.js','src/styles.css':'styles.css','public/favicon.svg':'favicon.svg'}.items()}
    import html
    files['index.html'] = '<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="/favicon.svg"><title>'+html.escape(design['title'])+'</title></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>'
    files['src/main.jsx'] = 'import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App.jsx";\nimport "./styles.css";\ncreateRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);\n'
    files['src/gameDesign.js']='export const GAME_DESIGN = '+json.dumps(design,ensure_ascii=False,indent=2)+';\n'
    files['.genesys-game-plan.json']=json.dumps({'version':2,'pipeline':'tested-foundation-with-agent-authored-design',
        'foundation':'survival-v1','designDecision':response.get('designDecision',''),
        'design':design,'validation':'Design bounds validated; browser playtests and screenshot review still required.'},indent=2)
    # Reuse the starter's supplied persistence helper. No model source or borrowed app state.
    return files

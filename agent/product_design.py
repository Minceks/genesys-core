"""Fast product classification and a persisted brief, without an extra model call."""
import json
import re
from .design_strategy import design_strategy, requests_redesign
from .layout_library import layout_reference_library
from .content_direction import content_direction
from .visual_system import visual_system

BRIEF_PATH = '.genesys-design.json'
PRODUCTS = {
    'game': r'\b(game|gaming|zombie|shooter|platformer|survival game)\b',
    'portfolio': r'\b(portfolio|photographer|photography)\b',
    'store': r'\b(store|shop|ecommerce|e-commerce|marketplace)\b|\b(?:sell|sells|selling)\s+(?:\w+\s+){0,2}(?:products?|goods|merchandise)\b',
    'dashboard': r'\b(dashboard|analytics dashboard|admin panel)\b',
    'app': r'\b(app|application|tracker|planner|task manager)\b',
    'website': r'\b(website|landing page|business site|blog|informational site)\b',
}
DIRECTIONS = {
    'game': {'layout':'Immersive playable scene with compact HUD, start/pause screens and mobile controls.',
        'visual':'Choose a world and genre appropriate atmosphere, depth, lighting, layered scenery, animated entities and readable HUD. Zombie survival calls for cinematic ruined environments, not portfolio cards or inherited brand styling.',
        'assets':'World scenery, character/enemy art or deliberate procedural graphics, hit effects and feedback.',
        'technology':'Use the existing rendering stack. For 2D/2.5D consider Canvas or an available game engine; for explicitly requested true 3D evaluate WebGL. Never claim a 2D canvas is full 3D.',
        'checks':['Start and restart the game', 'Movement/shooting or genre-specific inputs work', 'HUD updates and mobile controls are usable']},
    'portfolio': {'layout':'Image-led hero, project/gallery presentation, project detail and contact.',
        'visual':'Editorial typography, generous spacing and restrained colors that let the work dominate.',
        'assets':'Actual photos/artwork; use provided assets first and clearly label stock samples.',
        'technology':'Responsive React with an accessible gallery/lightbox when required.',
        'checks':['Images load', 'Gallery and detail interactions work', 'Contact actions have a real destination']},
    'store': {'layout':'Editorial merchandise hero, curated collection, search/category/sort discovery, product detail with quantity and saved items, useful comparison, basket, checkout and local order history.',
        'visual':'Substantial product imagery, deliberate typography, varied editorial sections, meaningful buying guidance and a coherent visual language through catalog, detail, cart and confirmation.',
        'assets':'Relevant product photos and truthful product information.',
        'technology':'React storefront; payments and inventory require real backend integrations, not fake success.',
        'checks':['Search, categories, sorting, reset and empty states work', 'Saved items and selected quantities persist correctly', 'Comparison uses truthful product information', 'Basket quantities and totals update', 'Local order history and cancellation work; payment integration status is accurate']},
    'dashboard': {'layout':'Navigation, summary metrics, meaningful charts, tables and filters.',
        'visual':'Readable data hierarchy, compact density, consistent units and restrained accent colors.',
        'assets':'Purposeful data visualizations; label demo data.',
        'technology':'React state and available chart libraries or semantic SVG; preserve data persistence.',
        'checks':['Filters update displayed data', 'Actions persist when appropriate', 'Empty and error states are usable']},
    'app': {'layout':'Organize screens around the primary user workflow and useful navigation.',
        'visual':'Clear interaction hierarchy, legible controls and purpose-specific styling.',
        'assets':'Use icons and imagery only where they help the workflow.',
        'technology':'React with appropriate state and persistence; shared data needs a backend.',
        'checks':['Primary workflow works', 'Validation and persistence work', 'Mobile navigation is usable']},
    'website': {'layout':'Purpose-specific page sections, clear navigation and a meaningful call to action.',
        'visual':'Brand and audience appropriate typography, coherent spacing and deliberate imagery.',
        'assets':'Relevant photos/illustrations, never empty image placeholders.',
        'technology':'Responsive semantic React/HTML with existing project dependencies.',
        'checks':['Navigation works', 'Calls to action work', 'Responsive sections do not overflow']},
}


def presentation_contract(product):
    if product in {'website', 'portfolio', 'store'}:
        return {
            'mode': 'public-website',
            'primaryExperience': 'A composed public website for visitors, with a distinct identity and content-led browsing.',
            'layoutRequirements': ['Meaningful header and navigation',
                'Designed hero with a clear headline, relevant visual and primary destination',
                'At least two purpose-specific content sections with varied composition',
                'Detail views or sections for the showcased content', 'Useful footer',
                'Intentional stacked phone layout'],
            'interactionPolicy': 'Navigation and calls to action must reach real sections, views or destinations. '
                'Add/edit/delete controls belong in a separate labeled management view only if requested '
                'or already implemented; preserve existing behavior while moving it.',
            'avoid': 'Do not turn a website into a spreadsheet, CRUD panel, generic metrics dashboard '
                'or a single repeated card grid. Do not invent administrative features. '
                'Tables are appropriate only for requested comparison/data sections, never the default page composition.',
        }
    return {'mode': 'workflow-app',
            'primaryExperience': 'Organize the interface around the requested workflow. '
                'Use tables/forms where they help; a playable game needs a scene, not a marketing hero.'}


def prepare_design(workspace, prompt):
    from .build_intent import replaces_product
    whole_product = replaces_product(prompt)
    redesign = requests_redesign(prompt)
    previous = None
    try:
        result = workspace.read_file(BRIEF_PATH)
        if result.get('truncated'):
            from .daytona_workspace import safe_remote_path
            raw = workspace.sandbox.fs.download_file(safe_remote_path(BRIEF_PATH))
            if len(raw) > 256000:
                raise ValueError('Saved design brief exceeds metadata limit')
            result = {'status':'success','content':raw.decode('utf-8')}
        previous = json.loads(result.get('content', '')) if result.get('status') == 'success' else None
        if not isinstance(previous, dict) or previous.get('productType') not in PRODUCTS:
            previous = None
    except (FileNotFoundError, ValueError, TypeError, AttributeError):
        previous = None
    selected = next((name for name, pattern in PRODUCTS.items() if re.search(pattern, prompt, re.I)), None)
    if (selected == 'game' and re.search(r'\b(website|site|blog|reviews|news|showcase)\b', prompt, re.I)
            and not re.search(r'\b(playable|movement|shooting|platformer|survival game)\b', prompt, re.I)):
        selected = 'website'
    replacement = bool(re.search(r'\b(build|create|make|replace|convert|turn|transform|redesign)\b', prompt, re.I))
    retain = previous and not whole_product and (not selected or selected == previous['productType'] or not replacement)
    if retain:
        brief = dict(previous)
        brief['latestRequest'] = prompt
        brief['designPolicy'] = 'Preserve the existing direction; apply explicit user changes only.'
        if redesign:
            brief['designPolicy'] = 'Refresh the visual direction as requested while preserving working behavior.'
    else:
        selected = selected or 'website'
        subtype = ('2.5D' if re.search(r'2[.]5d', prompt, re.I) else '3D' if re.search(r'\b3d\b', prompt, re.I) else '2D') if selected == 'game' else selected
        brief = {'version':1, 'productType':selected, 'subtype':subtype,
                 'originalRequest':prompt, 'latestRequest':prompt,
                 'designPolicy':'Choose a direction suited to this product. Explicit user preferences override recommendations.',
                 **DIRECTIONS[selected]}
        if previous:
            brief['purposeChangedFrom'] = previous['productType']
            brief['designPolicy'] += ' The product purpose changed; replace unsuitable inherited theme and layout.'
    brief['buildIntent'] = 'replace-product' if previous and whole_product else 'edit-product' if retain else 'new-product'
    if brief['productType'] == 'game':
        brief['interactiveRuntime'] = (
            'Use one authoritative simulation state in a ref or engine store and a single cancellable '
            'requestAnimationFrame loop; React state mirrors HUD values rather than owning each frame. '
            'Never capture initial state in a permanent animation/event callback. Stop scheduling on '
            'unmount and terminal outcomes. Pause freezes the same scene and clears held inputs; Resume '
            'continues that exact run, Restart explicitly resets it. Scale pointer coordinates from the '
            'rendered canvas to its logical dimensions. Implement real touch joystick/fire controls when '
            'offered; settings must change actual inputs. Clear held input on blur/pointercancel. '
            'Keep the canvas keyboard-focusable and expose live health, score, wave and outcomes as '
            'accessible HUD text. Persist progress only after an actual completed run. Verify movement, '
            'combat, pause/resume and touch interactions through real inputs; never create shortcuts '
            'or fake outcomes for verification.')
    if previous and whole_product:
        brief['designPolicy'] = ('Replace the website/application in THIS project with the newly requested product. '
            'The latest request supersedes the old product brief, brand, content and feature requirements. '
            'Reuse compatible infrastructure, not unrelated old pages or data. Preserve old stored records without '
            'reinterpreting them as the new product; namespace new records. Do not create a separate project. '
            'Implement actual requested workflows; unavailable AI/backend integrations must be disclosed, never faked.')
    if not brief.get('designResearch') or redesign:
        from .design_research import research_design
        brief['designResearch'] = research_design(prompt, brief['productType'])
    if brief['designResearch']['family'] == 'gaming-editorial':
        brief['visual'] = ('Modern gaming editorial: large featured artwork, bold condensed headings, '
            'cinematic crops, clear rankings and image-led asymmetric sections. Consider a dark '
            'neutral palette and restrained bright accent unless the user specifies another style. '
            'Keep administration separate from the public showcase; avoid generic beige CRUD cards.')
        brief['layout'] = 'Featured game hero, curated ranked discoveries, genre/platform browsing and focused game detail.'
    brief['presentationContract'] = presentation_contract(brief['productType'])
    brief['contentDirection'] = content_direction(
        prompt, (previous or {}).get('contentDirection') if retain else content_direction(brief['originalRequest']),
    )
    if redesign or not brief.get('designStrategy') or not retain:
        brief['designStrategy'] = design_strategy(
            getattr(workspace, 'project_id', 'genesys-project'), brief['productType'], prompt, previous if retain else None, redesign,
        )
    elif brief.get('designStrategy'):
        brief['designStrategy'] = {**brief['designStrategy'], 'redesign': False,
                                   'redesignRequirements': []}
    if redesign:
        brief['designPolicy'] = ('Perform a visibly distinct redesign using designStrategy alternatives. '
            'Inspect the current UI and stylesheet; preserve working functionality and saved data. '
            'Repairing defects alone does not satisfy this request. Change the composition, hierarchy '
            'and visual treatment while honoring explicit user preferences.')
    brief['layoutReferences'] = layout_reference_library(
        brief['productType'], prompt, brief['designStrategy'],
    )
    if redesign or not retain or not brief.get('visualSystem'):
        brief['visualSystem'] = visual_system(getattr(workspace, 'project_id', 'genesys-project'),
            brief['productType'], prompt if redesign else brief['originalRequest'] + '\n' + prompt, brief['designStrategy'])
    brief['integrationPolicy'] = {
        'payments': 'Real payment processing is deferred unless explicitly requested with a working integration. '
                    'Build a polished local basket, order summary, validation and cancellation. Preserve the basket; '
                    'never claim payment/order completion. Explain availability only at the payment step, '
                    'not in the homepage hero or product cards.',
    }
    from .experience_blueprint import experience_blueprint
    brief['experienceBlueprint'] = experience_blueprint(brief)
    from .reference_inspection import prepare_reference
    reference = prepare_reference(workspace, prompt, brief, previous if retain else None, redesign)
    if reference:
        brief['referenceAnalysis'] = reference
    brief['qualityStandard'] = {
        'composition': 'Distinctive focal point, purposeful section rhythm and product-appropriate density.',
        'typography': 'Coherent type hierarchy, readable body copy and deliberate line lengths.',
        'consistency': 'Shared spacing, color, border and control tokens; aligned visual edges.',
        'presentation': 'Show the user-facing product first; keep management tools out of visitor-facing hero content.',
        'responsive': 'Intentional phone layout, reachable actions, no hover-only functionality.',
        'finish': 'Real relevant imagery, concise copy, polished interaction states and preserved working behavior.',
    }
    from .design_foundation import prepare_foundation
    foundation = prepare_foundation(workspace, brief['visualSystem'], previous)
    if foundation:
        brief['designFoundation'] = foundation
    # Keep the implementable art direction near the beginning when provider
    # context limits shorten a large brief or a parallel worker's first message.
    from .design_execution import design_execution
    brief['designExecution'] = design_execution(brief)
    brief = {'visualSystem': brief['visualSystem'], 'experienceBlueprint': brief['experienceBlueprint'], 'designExecution': brief['designExecution'],
             **({'referenceAnalysis': brief['referenceAnalysis']} if brief.get('referenceAnalysis') else {}),
             **{key: value for key, value in brief.items() if key not in {'visualSystem', 'experienceBlueprint', 'designExecution', 'referenceAnalysis'}}}
    saved = workspace.write_file(BRIEF_PATH, json.dumps(brief, ensure_ascii=False, indent=2))
    if not isinstance(saved, dict) or saved.get('status') != 'success':
        raise RuntimeError('Could not save project design brief')
    return brief
